from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from livethetrader.logging import get_logger, log_event

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class PollResult:
    payload: dict[str, Any] | None
    connected: bool
    error: str | None


class BackendPollingClient:
    """Simple HTTP polling client with reconnect support for the UI layer."""

    def __init__(
        self,
        base_url: str,
        endpoint: str = "/api/v1/dashboard",
        timeout: float = 2.0,
        reconnect_backoff: float = 1.0,
        max_backoff: float = 8.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.timeout = timeout
        self.reconnect_backoff = reconnect_backoff
        self.max_backoff = max_backoff
        self._current_backoff = reconnect_backoff

    def _request(self) -> dict[str, Any]:
        request = Request(f"{self.base_url}{self.endpoint}", headers={"Accept": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            raw_body = response.read().decode("utf-8")
        return json.loads(raw_body)

    def poll_once(self) -> PollResult:
        try:
            payload = self._request()
            self._current_backoff = self.reconnect_backoff
            log_event(
                LOGGER,
                "interface_poll_success",
                base_url=self.base_url,
                endpoint=self.endpoint,
            )
            return PollResult(payload=payload, connected=True, error=None)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            wait_seconds = self._current_backoff
            log_event(
                LOGGER,
                "interface_poll_error",
                level=30,
                base_url=self.base_url,
                endpoint=self.endpoint,
                error=str(exc),
                backoff_seconds=wait_seconds,
            )
            time.sleep(wait_seconds)
            self._current_backoff = min(self._current_backoff * 2, self.max_backoff)
            return PollResult(payload=None, connected=False, error=str(exc))
