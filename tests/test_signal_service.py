from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from livethetrader.api.service import TradingSignalService
from livethetrader.config import AppConfig
from livethetrader.ingestion.mock_source import MockTickSource
from livethetrader.ingestion.real_adapter import RealTickSourceAdapter
from livethetrader.market_data.aggregator import MultiTimeframeCandleBuilder


class _StubStrategy:
    def __init__(self, confidence: float) -> None:
        self._confidence = confidence

    def evaluate(self, features_by_tf: dict[str, dict[str, float]]) -> tuple[str, float, list[str]]:
        return "CALL", self._confidence, ["stub_strategy"]


class _PassThroughGate:
    def approve(
        self,
        *,
        strategy_direction: str,
        risk_direction: str,
        features: dict[str, float],
    ) -> tuple[str, float, list[str]]:
        return risk_direction, 0.9, ["stub_gate"]


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


def test_signal_engine_risk_thresholds_from_config_change_decision() -> None:
    strict_config = AppConfig()
    strict_config.thresholds.confidence_min = 0.75
    strict_config.thresholds.risk_rejection_max = 0.5
    strict_service = TradingSignalService(symbol="EURUSD", config=strict_config)
    strict_service.engine.strategy = _StubStrategy(confidence=0.6)
    strict_service.engine.publication_gate = _PassThroughGate()

    permissive_config = AppConfig()
    permissive_config.thresholds.confidence_min = 0.55
    permissive_config.thresholds.risk_rejection_max = 0.45
    permissive_service = TradingSignalService(symbol="EURUSD", config=permissive_config)
    permissive_service.engine.strategy = _StubStrategy(confidence=0.6)
    permissive_service.engine.publication_gate = _PassThroughGate()

    strict_signal = strict_service.engine.generate(symbol="EURUSD", features_by_tf={"1m": {}})
    permissive_signal = permissive_service.engine.generate(symbol="EURUSD", features_by_tf={"1m": {}})

    assert strict_signal.direction == "NEUTRO"
    assert "confidence_below_threshold" in strict_signal.reason_codes
    assert permissive_signal.direction == "CALL"
    assert "risk_ok" in permissive_signal.reason_codes


def test_signal_engine_applies_rejection_threshold_from_config() -> None:
    config = AppConfig()
    config.thresholds.confidence_min = 0.7
    config.thresholds.risk_rejection_max = 0.6
    service = TradingSignalService(symbol="EURUSD", config=config)
    service.engine.strategy = _StubStrategy(confidence=0.6)
    service.engine.publication_gate = _PassThroughGate()

    signal = service.engine.generate(symbol="EURUSD", features_by_tf={"1m": {}})

    assert signal.direction == "NEUTRO"
    assert "confidence_below_rejection_threshold" in signal.reason_codes
