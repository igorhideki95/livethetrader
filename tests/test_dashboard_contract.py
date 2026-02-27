from __future__ import annotations

import pytest

from livethetrader.dashboard import DashboardContractError, normalize_dashboard_payload
from livethetrader.interface.service import build_local_dashboard_payload


def test_build_local_dashboard_payload_includes_schema_version_and_trades_total() -> None:
    payload = build_local_dashboard_payload(
        {
            "symbol": "EURUSD",
            "direction": "CALL",
            "confidence": 0.71,
            "timestamp_open": "2026-01-01T10:00:00Z",
        }
    )

    assert set(payload) >= {"schema_version", "status", "updated_at", "current_signal", "metrics"}
    assert payload["schema_version"] == "1.0.0"
    assert set(payload["metrics"]) >= {"win_rate", "profit_factor", "drawdown", "trades_total"}
    assert payload["metrics"]["trades_total"] == payload["metrics"]["trades"]


def test_normalize_dashboard_payload_accepts_legacy_metrics_alias() -> None:
    payload = {
        "schema_version": "1.0.0",
        "status": "running",
        "updated_at": "2026-01-01T10:00:00Z",
        "current_signal": {
            "direction": "PUT",
            "confidence": 0.44,
            "timestamp": "2026-01-01T10:00:00Z",
        },
        "metrics": {"win_rate": 0.5, "profit_factor": 1.1, "drawdown": 0.2, "trades": 12},
    }

    normalized = normalize_dashboard_payload(payload)

    assert normalized["metrics"]["trades_total"] == 12
    assert normalized["metrics"]["trades"] == 12


def test_normalize_dashboard_payload_rejects_unsupported_schema_version() -> None:
    invalid_payload = {
        "schema_version": "2.0.0",
        "status": "running",
        "updated_at": "2026-01-01T10:00:00Z",
        "current_signal": {
            "direction": "CALL",
            "confidence": 0.7,
            "timestamp": "2026-01-01T10:00:00Z",
        },
        "metrics": {"win_rate": 0.6, "profit_factor": 1.2, "drawdown": 0.1, "trades_total": 9},
    }

    with pytest.raises(DashboardContractError):
        normalize_dashboard_payload(invalid_payload)
