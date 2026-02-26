from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Any

from livethetrader.config import AppConfig, load_config
from livethetrader.indicators.service import IndicatorService
from livethetrader.ingestion.base import TickSource
from livethetrader.ingestion.mock_source import MockTickSource
from livethetrader.ingestion.real_adapter import ProviderConfig, RealTickSourceAdapter
from livethetrader.logging import configure_logging, get_logger, log_event
from livethetrader.market_data.aggregator import MultiTimeframeCandleBuilder
from livethetrader.models import Tick
from livethetrader.signal_engine.engine import SignalEngine

LOGGER = get_logger(__name__)


class TradingSignalService:
    """Facade that returns CALL|PUT|NEUTRO + confidence + expiry."""

    def __init__(
        self,
        symbol: str = "EURUSD",
        config: AppConfig | None = None,
        message_stream_factory: Callable[[ProviderConfig], Iterator[Any]] | None = None,
    ) -> None:
        self.config = config or load_config()
        configure_logging(
            level=self.config.logging.level,
            service_name=self.config.logging.service_name,
        )
        self.symbol = symbol
        self.source = self._build_source(message_stream_factory=message_stream_factory)
        self.builder = MultiTimeframeCandleBuilder(symbol=symbol)
        self.indicators = IndicatorService()
        self.engine = SignalEngine(config=self.config)

    def _build_source(
        self,
        *,
        message_stream_factory: Callable[[ProviderConfig], Iterator[Any]] | None = None,
    ) -> TickSource:
        provider_endpoint = self.config.endpoints.provider_endpoint.strip()
        if not provider_endpoint:
            return MockTickSource(symbol=self.symbol)

        provider_config = ProviderConfig(
            provider_name=self.config.provider.provider_name or "provider",
            symbol=self.config.provider.symbol or self.symbol,
            endpoint=provider_endpoint,
            credentials=dict(self.config.provider.credentials),
        )
        return RealTickSourceAdapter(
            config=provider_config,
            message_stream_factory=message_stream_factory,
        )

    def _iter_ticks(self, *, count: int) -> Iterator[Tick]:
        if isinstance(self.source, MockTickSource):
            yield from self.source.stream(count=count)
            return

        for idx, tick in enumerate(self.source.stream()):
            if idx >= count:
                break
            yield tick

    def run_once(self, tick_count: int | None = None) -> dict:
        resolved_tick_count = tick_count or self.config.limits.max_ticks_per_run
        log_event(
            LOGGER,
            "api_run_once_started",
            symbol=self.symbol,
            tick_count=resolved_tick_count,
        )

        features_by_tf: dict[str, dict[str, float]] = defaultdict(dict)
        for tick in self._iter_ticks(count=resolved_tick_count):
            closed_candles = self.builder.update(tick)
            for candle in closed_candles:
                features = self.indicators.push(candle)
                if features:
                    features_by_tf[candle.timeframe] = features

        signal = self.engine.generate(symbol=self.symbol, features_by_tf=features_by_tf)
        payload = signal.to_contract()
        log_event(
            LOGGER,
            "api_run_once_completed",
            symbol=self.symbol,
            direction=payload["direction"],
            confidence=payload["confidence"],
        )
        return payload
