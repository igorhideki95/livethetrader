from __future__ import annotations

import json
import time
from urllib import request

from livethetrader.api.http_server import shutdown_dashboard_http_server
from livethetrader.interface.console import _start_local_server
from livethetrader.ui.models import build_snapshot


def _request_json(base_url: str, method: str, path: str) -> tuple[int, dict]:
    req = request.Request(
        url=f"{base_url}{path}",
        method=method,
        headers={"Accept": "application/json"},
    )
    with request.urlopen(req, timeout=3.0) as response:  # noqa: S310
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def test_get_dashboard_matches_ui_contract() -> None:
    server = _start_local_server(0)
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        status, payload = _request_json(base_url, "GET", "/api/v1/dashboard")

        assert status == 200
        assert payload["schema_version"] == "1.0.0"
        assert payload["symbol"] == "EURUSD"
        assert payload["timeframe"] == "1m"
        assert payload["status"] in {"running", "paused", "offline", "online"}
        assert payload["system_status"] == payload["status"].upper()
        assert set(payload["current_signal"]) >= {"direction", "confidence", "timestamp"}
        assert isinstance(payload["candles"], list)
        assert isinstance(payload["history"], list)
        assert payload["metrics"]["trades_total"] == payload["metrics"]["trades"]

        adapted = build_snapshot(payload)
        assert adapted.schema_version == payload["schema_version"]
        assert adapted.symbol == payload["symbol"]
        assert adapted.timeframe == payload["timeframe"]
        assert adapted.system_status == payload["system_status"]
        assert adapted.status == payload["status"]
        assert adapted.current_signal.direction == payload["current_signal"]["direction"]
    finally:
        server.shutdown()
        shutdown_dashboard_http_server(server)
        server.server_close()


def test_dashboard_control_endpoints_change_processing_state() -> None:
    server = _start_local_server(0)
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        start_status, _ = _request_json(base_url, "POST", "/api/v1/dashboard/control/start")
        assert start_status == 200

        time.sleep(0.5)
        _, running_payload = _request_json(base_url, "GET", "/api/v1/dashboard")
        running_history_size = len(running_payload["history"])
        assert running_payload["status"] == "running"
        assert running_history_size > 0

        pause_status, _ = _request_json(base_url, "POST", "/api/v1/dashboard/control/pause")
        assert pause_status == 200

        time.sleep(0.4)
        _, paused_payload = _request_json(base_url, "GET", "/api/v1/dashboard")
        assert paused_payload["status"] == "paused"
        assert len(paused_payload["history"]) == running_history_size

        restart_status, _ = _request_json(base_url, "POST", "/api/v1/dashboard/control/restart")
        assert restart_status == 200

        reload_status, reload_payload = _request_json(
            base_url,
            "POST",
            "/api/v1/dashboard/control/reload-config",
        )
        assert reload_status == 200
        assert reload_payload["ok"] is True
        assert reload_payload["message"] == "Configuração recarregada."

        time.sleep(0.5)
        _, restarted_payload = _request_json(base_url, "GET", "/api/v1/dashboard")
        assert restarted_payload["status"] == "running"
        assert len(restarted_payload["history"]) > 0
        assert restarted_payload["updated_at"] >= paused_payload["updated_at"]
    finally:
        server.shutdown()
        shutdown_dashboard_http_server(server)
        server.server_close()
