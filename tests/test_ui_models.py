from livethetrader.ui.models import HistoryTrade, build_snapshot, derive_metrics_from_history


def test_derive_metrics_from_history() -> None:
    history = [
        HistoryTrade(
            time="2026-01-01T10:00:00Z",
            symbol="EURUSD",
            signal="CALL",
            confidence=0.7,
            result="WIN",
            pnl=10,
        ),
        HistoryTrade(
            time="2026-01-01T10:05:00Z",
            symbol="EURUSD",
            signal="PUT",
            confidence=0.6,
            result="LOSS",
            pnl=-5,
        ),
    ]

    metrics = derive_metrics_from_history(history)

    assert metrics.trades == 2
    assert metrics.win_rate == 0.5
    assert metrics.profit_factor == 2.0
    assert metrics.drawdown == 5.0
    assert metrics.expectancy == 2.5
    assert metrics.equity_curve is not None
    assert [p.equity for p in metrics.equity_curve] == [10.0, 5.0]


def test_build_snapshot_uses_history_metrics_fallback() -> None:
    payload = {
        "status": "running",
        "current_signal": {"direction": "CALL", "confidence": 0.8},
        "history": [
            {
                "time": "2026-01-01T10:00:00Z",
                "symbol": "EURUSD",
                "signal": "CALL",
                "confidence": 0.8,
                "result": "WIN",
                "pnl": 8,
            }
        ],
    }

    snapshot = build_snapshot(payload)

    assert snapshot.status == "running"
    assert snapshot.current_signal.direction == "CALL"
    assert snapshot.metrics.trades == 1
    assert snapshot.metrics.win_rate == 1.0
