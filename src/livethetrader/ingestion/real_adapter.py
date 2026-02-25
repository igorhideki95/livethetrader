from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from livethetrader.ingestion.base import TickSource
from livethetrader.models import Tick

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderConfig:
    provider_name: str
    symbol: str
    endpoint: str
    credentials: dict[str, str] = field(default_factory=dict)
    heartbeat_seconds: float = 1.0
    request_timeout_seconds: float = 10.0
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    backoff_multiplier: float = 2.0


class RealTickSourceAdapter(TickSource):
    """Tick source backed by API/WebSocket provider with retry and normalization."""

    def __init__(
        self,
        provider_name: str | None = None,
        *,
        config: ProviderConfig | None = None,
        message_stream_factory: Callable[[ProviderConfig], Iterator[Any]] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if config is None:
            if provider_name is None:
                raise ValueError("Either provider_name or config must be provided")
            config = ProviderConfig(provider_name=provider_name, symbol="", endpoint="")

        self.config = config
        self.provider_name = config.provider_name
        self._message_stream_factory = message_stream_factory or self._default_message_stream
        self._sleep = sleep_fn or time.sleep
        self._logger = logger or LOGGER

    def stream(self) -> Iterator[Tick]:
        if not self.config.endpoint:
            raise ValueError("Provider endpoint is required")
        if not self.config.symbol:
            raise ValueError("Provider symbol is required")

        attempt = 0
        while True:
            self._log(
                "connection_start",
                endpoint=self.config.endpoint,
                symbol=self.config.symbol,
                attempt=attempt + 1,
            )
            try:
                for message in self._message_stream_factory(self.config):
                    tick = self._to_tick(message)
                    if tick is None:
                        continue
                    attempt = 0
                    yield tick
            except Exception as exc:  # noqa: BLE001 - keep stream resilient
                backoff = min(
                    self.config.max_backoff_seconds,
                    self.config.initial_backoff_seconds * (self.config.backoff_multiplier**attempt),
                )
                self._log(
                    "connection_error",
                    level=logging.ERROR,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    backoff_seconds=backoff,
                    attempt=attempt + 1,
                )
                self._sleep(backoff)
                attempt += 1
                self._log(
                    "connection_resume",
                    backoff_seconds=backoff,
                    next_attempt=attempt + 1,
                )

    def _default_message_stream(self, config: ProviderConfig) -> Iterator[Any]:
        if config.endpoint.startswith(("ws://", "wss://")):
            yield from self._websocket_message_stream(config)
            return

        while True:
            yield self._fetch_api_payload(config)
            self._sleep(config.heartbeat_seconds)

    def _websocket_message_stream(self, config: ProviderConfig) -> Iterator[Any]:
        try:
            import websocket  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("websocket-client package is required for ws/wss endpoints") from exc

        ws = websocket.create_connection(
            config.endpoint,
            timeout=config.request_timeout_seconds,
            header=self._headers(config),
        )
        try:
            auth_payload = config.credentials.get("auth_payload")
            if auth_payload:
                ws.send(auth_payload)

            while True:
                raw = ws.recv()
                if raw is None:
                    raise RuntimeError("WebSocket closed by provider")
                yield raw
        finally:
            ws.close()

    def _fetch_api_payload(self, config: ProviderConfig) -> Any:
        request = Request(config.endpoint, headers=self._headers(config))
        try:
            with urlopen(request, timeout=config.request_timeout_seconds) as response:  # noqa: S310
                payload = response.read().decode("utf-8")
        except URLError as exc:
            raise RuntimeError(f"Failed to reach provider API: {exc}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def _headers(self, config: ProviderConfig) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        api_key = config.credentials.get("api_key")
        if api_key:
            header_name = config.credentials.get("api_key_header", "Authorization")
            prefix = config.credentials.get("api_key_prefix", "Bearer ")
            headers[header_name] = f"{prefix}{api_key}" if prefix else api_key
        return headers

    def _to_tick(self, message: Any) -> Tick | None:
        payload: dict[str, Any]
        if isinstance(message, str):
            try:
                parsed = json.loads(message)
            except json.JSONDecodeError:
                self._log("parse_error", level=logging.WARNING, raw_message=message)
                return None
            payload = parsed if isinstance(parsed, dict) else {}
        elif isinstance(message, dict):
            payload = message
        else:
            self._log("parse_error", level=logging.WARNING, raw_message=str(message))
            return None

        try:
            timestamp = self._normalize_timestamp(
                payload.get("timestamp") or payload.get("time") or payload.get("ts")
            )
            bid = self._normalize_float(payload.get("bid"), field_name="bid")
            ask = self._normalize_float(payload.get("ask"), field_name="ask")
            last = self._normalize_float(
                payload.get("last") or payload.get("price"), field_name="last"
            )
            volume = self._normalize_float(
                payload.get("volume") or payload.get("qty") or 0.0,
                field_name="volume",
            )
        except ValueError as exc:
            self._log("validation_error", level=logging.WARNING, error=str(exc), payload=payload)
            return None

        return Tick(
            symbol=self.config.symbol,
            timestamp=timestamp,
            bid=bid,
            ask=ask,
            last=last,
            volume=volume,
        )

    def _normalize_timestamp(self, raw: Any) -> datetime:
        if raw is None:
            raise ValueError("timestamp is required")

        if isinstance(raw, (int, float)):
            value = float(raw)
            if value > 1e12:  # ms epoch
                value /= 1000.0
            return datetime.fromtimestamp(value, tz=timezone.utc)

        if isinstance(raw, str):
            ts = raw.strip()
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            parsed = datetime.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)

        raise ValueError(f"invalid timestamp type: {type(raw).__name__}")

    def _normalize_float(self, raw: Any, *, field_name: str) -> float:
        if raw is None:
            raise ValueError(f"{field_name} is required")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid {field_name}: {raw!r}") from exc
        if value != value:
            raise ValueError(f"invalid {field_name}: NaN")
        return value

    def _log(self, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
        record = {
            "event": event,
            "provider": self.provider_name,
            "symbol": self.config.symbol,
            **fields,
        }
        self._logger.log(level, json.dumps(record, default=str))
