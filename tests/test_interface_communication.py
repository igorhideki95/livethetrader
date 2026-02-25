from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from livethetrader.interface.client import BackendPollingClient
from livethetrader.interface.service import InterfaceService


class _FlakyDashboardHandler(BaseHTTPRequestHandler):
    call_count = 0

    def do_GET(self) -> None:  # noqa: N802
        _FlakyDashboardHandler.call_count += 1
        if self.path != "/api/v1/dashboard":
            self.send_response(404)
            self.end_headers()
            return

        if _FlakyDashboardHandler.call_count == 1:
            self.send_response(500)
            self.end_headers()
            return

        payload = {
            "symbol": "EURUSD",
            "timeframe": "1m",
            "last_signal": "CALL",
            "confidence": 0.74,
            "system_status": "ONLINE",
            "metrics": {
                "win_rate": 0.58,
                "profit_factor": 1.4,
                "drawdown": 0.07,
                "trades_total": 55,
            },
            "history": [
                {
                    "signal_id": "sig_1",
                    "symbol": "EURUSD",
                    "timeframe": "1m",
                    "direction": "CALL",
                    "confidence": 0.74,
                    "timestamp_open": "2025-01-01T10:00:00Z",
                }
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _run_test_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FlakyDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def test_polling_client_reconnects_after_error():
    _FlakyDashboardHandler.call_count = 0
    server, base_url = _run_test_server()
    try:
        client = BackendPollingClient(base_url=base_url, reconnect_backoff=0.01, max_backoff=0.02)

        first_attempt = client.poll_once()
        assert first_attempt.connected is False
        assert first_attempt.payload is None

        second_attempt = client.poll_once()
        assert second_attempt.connected is True
        assert second_attempt.payload is not None
        assert second_attempt.payload["last_signal"] == "CALL"
    finally:
        server.shutdown()


def test_interface_service_returns_snapshot_with_metrics_and_history():
    _FlakyDashboardHandler.call_count = 1
    server, base_url = _run_test_server()
    try:
        client = BackendPollingClient(base_url=base_url, reconnect_backoff=0.01, max_backoff=0.02)
        interface = InterfaceService(client=client)

        snapshot, error = interface.fetch_snapshot()

        assert error is None
        assert snapshot is not None
        assert snapshot.symbol == "EURUSD"
        assert snapshot.metrics.trades_total == 55
        assert snapshot.history[0].signal_id == "sig_1"
    finally:
        server.shutdown()
