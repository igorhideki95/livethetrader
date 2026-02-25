from datetime import datetime, timedelta, timezone

import pytest

from livethetrader.backtest import BacktestRunner, DeploymentBlockedError, StrategyDeploymentGate
from livethetrader.models import Candle


def _build_candles(symbol: str, timeframe: str, closes: list[float]) -> list[Candle]:
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    for idx, close in enumerate(closes):
        ts_open = base + timedelta(minutes=idx)
        ts_close = ts_open + timedelta(minutes=1)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp_open=ts_open,
                timestamp_close=ts_close,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=100,
            )
        )
    return candles


def test_backtest_report_contains_required_metrics_and_comparisons(tmp_path):
    closes = [1.0, 1.002, 1.001, 1.004, 1.003, 1.005, 1.007, 1.006, 1.009, 1.011, 1.008, 1.01]
    directions = ["CALL", "PUT", "CALL", "CALL", "PUT", "CALL", "PUT", "CALL", "CALL", "PUT", "CALL"]
    candles = _build_candles("EURUSD", "1m", closes)

    runner = BacktestRunner()
    report = runner.run(
        symbol="EURUSD",
        candles=candles,
        directions=directions,
        report_output_dir=str(tmp_path / "reports"),
    )

    assert "win_rate" in report
    assert "profit_factor" in report
    assert "expectancy" in report
    assert "max_drawdown" in report
    assert report["comparison_by_asset_timeframe"]["EURUSD:1m"]["trades_total"] >= 1
    assert "bull" in report["comparison_by_market_regime"]
    assert "sideways" in report["comparison_by_market_regime"]

    assert report["report_path"].endswith(".json")


def test_deploy_gate_blocks_strategy_below_dod_baseline():
    gate = StrategyDeploymentGate()
    bad_report = {
        "win_rate": 0.4,
        "profit_factor": 0.9,
        "expectancy": -0.1,
        "max_drawdown": -0.05,
    }

    with pytest.raises(DeploymentBlockedError):
        gate.validate(bad_report)
