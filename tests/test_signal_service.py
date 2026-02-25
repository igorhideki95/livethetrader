from livethetrader.api.service import TradingSignalService
from livethetrader.ingestion.mock_source import MockTickSource
from livethetrader.market_data.aggregator import MultiTimeframeCandleBuilder


def test_candle_aggregation_includes_1m_5m_15m():
    source = MockTickSource(seed=10)
    builder = MultiTimeframeCandleBuilder(symbol="EURUSD")
    counts = {"1m": 0, "5m": 0, "15m": 0}

    for tick in source.stream(count=3600):
        for candle in builder.update(tick):
            counts[candle.timeframe] += 1

    assert counts["1m"] > 0
    assert counts["5m"] > 0
    assert counts["15m"] > 0


def test_service_returns_standard_output():
    service = TradingSignalService(symbol="EURUSD")
    payload = service.run_once(tick_count=54000)

    assert payload["direction"] in {"CALL", "PUT", "NEUTRO"}
    assert 0 <= payload["confidence"] <= 1
    assert payload["expiry"].endswith("m")
    assert payload["timeframe"] == "1m"
