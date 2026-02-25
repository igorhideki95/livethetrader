from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from livethetrader.api.service import TradingSignalService
from livethetrader.config import AppConfig
from livethetrader.ingestion.mock_source import MockTickSource
from livethetrader.ingestion.real_adapter import RealTickSourceAdapter
from livethetrader.market_data.aggregator import MultiTimeframeCandleBuilder


def test_candle_aggregation_includes_1m_5m_15m() -> None:
    source = MockTickSource(seed=10)
    builder = MultiTimeframeCandleBuilder(symbol="EURUSD")
    counts = {"1m": 0, "5m": 0, "15m": 0}

    for tick in source.stream(count=3600):
        for candle in builder.update(tick):
            counts[candle.timeframe] += 1

    assert counts["1m"] > 0
    assert counts["5m"] > 0
    assert counts["15m"] > 0


def test_service_returns_standard_output() -> None:
    service = TradingSignalService(symbol="EURUSD")
    payload = service.run_once(tick_count=54000)

    assert payload["direction"] in {"CALL", "PUT", "NEUTRO"}
    assert 0 <= payload["confidence"] <= 1
    assert payload["expiry"].endswith("m")
    assert payload["timeframe"] == "1m"


def test_source_selection_uses_mock_without_provider_endpoint() -> None:
    config = AppConfig()
    config.endpoints.provider_endpoint = ""

    service = TradingSignalService(symbol="EURUSD", config=config)

    assert isinstance(service.source, MockTickSource)


def test_source_selection_uses_real_adapter_with_provider_settings() -> None:
    config = AppConfig()
    config.endpoints.provider_endpoint = "https://provider.local/ticks"
    config.provider.provider_name = "my-provider"
    config.provider.symbol = "GBPUSD"
    config.provider.credentials = {"api_key": "abc123"}

    service = TradingSignalService(symbol="EURUSD", config=config)

    assert isinstance(service.source, RealTickSourceAdapter)
    assert service.source.config.provider_name == "my-provider"
    assert service.source.config.symbol == "GBPUSD"
    assert service.source.config.credentials == {"api_key": "abc123"}


def test_run_once_with_real_adapter_via_fake_message_stream_factory() -> None:
    config = AppConfig()
    config.endpoints.provider_endpoint = "https://provider.local/ticks"
    config.provider.provider_name = "fake-provider"

    def fake_feed(_: Any) -> Iterator[Any]:
        for index in range(70):
            yield {
                "timestamp": 1_735_740_000 + index,
                "bid": 1.1000,
                "ask": 1.1002,
                "last": 1.1001,
                "volume": 10,
            }

    service = TradingSignalService(
        symbol="EURUSD",
        config=config,
        message_stream_factory=fake_feed,
    )

    payload = service.run_once(tick_count=65)

    assert payload["direction"] in {"CALL", "PUT", "NEUTRO"}
    assert 0 <= payload["confidence"] <= 1
