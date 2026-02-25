from __future__ import annotations

import json
from urllib import request

from livethetrader.interface.console import _start_local_server
from livethetrader.interface.models import DashboardSnapshot


def _request_json(base_url: str, method: str, path: str) -> tuple[int, dict]:
    req = request.Request(
        url=f"{base_url}{path}",
        method=method,
        headers={"Accept": "application/json"},
    )
    with request.urlopen(req, timeout=2.0) as response:  # noqa: S310
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def test_get_dashboard_matches_ui_contract() -> None:
    server = _start_local_server(0)
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        status, payload = _request_json(base_url, "GET", "/api/v1/dashboard")

        assert status == 200
        assert payload["status"] in {"running", "online", "paused", "offline"}
        assert isinstance(payload["updated_at"], str)
        assert set(payload["current_signal"]) >= {"direction", "confidence", "timestamp"}
        assert isinstance(payload["candles"], list)
        assert isinstance(payload["history"], list)

        metrics = payload["metrics"]
        assert set(metrics) >= {
            "win_rate",
            "profit_factor",
            "drawdown",
            "trades",
            "expectancy",
            "equity_curve",
        }

        adapted = DashboardSnapshot.from_payload(payload)
        assert adapted.last_signal == payload["current_signal"]["direction"]
        assert adapted.metrics.trades_total == payload["metrics"]["trades"]
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_control_endpoints_return_ok_message() -> None:
    server = _start_local_server(0)
    base_url = f"http://127.0.0.1:{server.server_port}"
    actions = ["start", "pause", "restart", "reload-config"]
    try:
        for action in actions:
            status, payload = _request_json(base_url, "POST", f"/api/v1/dashboard/control/{action}")
            assert status == 200
            assert payload["ok"] is True
            assert isinstance(payload["message"], str)
            assert payload["message"]
    finally:
        server.shutdown()
        server.server_close()
