from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from livethetrader.api.service import TradingSignalService
from livethetrader.config import load_config
from livethetrader.interface.client import BackendPollingClient
from livethetrader.interface.models import DashboardSnapshot
from livethetrader.interface.service import InterfaceService, build_local_dashboard_payload
from livethetrader.logging import configure_logging, get_logger, log_event

LOGGER = get_logger(__name__)


class _LocalDashboardHandler(BaseHTTPRequestHandler):
    service = TradingSignalService(symbol="EURUSD")

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/api/v1/dashboard":
            self.send_response(404)
            self.end_headers()
            return

        signal = self.service.run_once(tick_count=6000)
        payload = build_local_dashboard_payload(signal_contract=signal)
        body = json.dumps(payload).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def render_snapshot(snapshot: DashboardSnapshot) -> str:
    lines = [
        "=" * 72,
        "LiveTheTrader Interface (MVP)",
        "=" * 72,
        f"Ativo: {snapshot.symbol}",
        f"Timeframe: {snapshot.timeframe}",
        f"Último sinal: {snapshot.last_signal}",
        f"Confiança: {snapshot.confidence:.2%}",
        f"Status do sistema: {snapshot.system_status}",
        "-" * 72,
        "Métricas:",
        f"  win_rate: {snapshot.metrics.win_rate:.2%}",
        f"  profit_factor: {snapshot.metrics.profit_factor:.2f}",
        f"  drawdown: {snapshot.metrics.drawdown:.2%}",
        f"  trades_total: {snapshot.metrics.trades_total}",
        "-" * 72,
        "Histórico de sinais (mais recentes):",
    ]

    for item in snapshot.history[-5:][::-1]:
        lines.append(
            f"  {item.timestamp_open.isoformat()} | {item.symbol} {item.timeframe} "
            f"| {item.direction} | conf={item.confidence:.2%}"
        )

    return "\n".join(lines)


def run_interface(base_url: str, interval: float = 2.0) -> None:
    client = BackendPollingClient(base_url=base_url)
    interface = InterfaceService(client=client)

    while True:
        snapshot, error = interface.fetch_snapshot()
        if error:
            log_event(LOGGER, "interface_loop_error", level=40, error=error)
            continue

        if snapshot:
            log_event(
                LOGGER,
                "interface_snapshot_rendered",
                rendered_snapshot=render_snapshot(snapshot),
            )
        time.sleep(interval)


def _start_local_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), _LocalDashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    config = load_config()
    configure_logging(level=config.logging.level, service_name=config.logging.service_name)

    parser = argparse.ArgumentParser(description="Terminal interface for LiveTheTrader")
    parser.add_argument("--base-url", default=config.endpoints.dashboard_base_url)
    parser.add_argument("--poll-interval", type=float, default=config.poll_interval_seconds)
    parser.add_argument("--local-backend", action="store_true", help="Run a local mock backend")
    parser.add_argument("--backend-port", type=int, default=8000)
    args = parser.parse_args()

    server = None
    try:
        if args.local_backend:
            server = _start_local_server(args.backend_port)
            args.base_url = f"http://127.0.0.1:{args.backend_port}"
            log_event(LOGGER, "local_backend_started", base_url=args.base_url)
        run_interface(base_url=args.base_url, interval=args.poll_interval)
    finally:
        if server:
            server.shutdown()
            log_event(LOGGER, "local_backend_shutdown")


if __name__ == "__main__":
    main()
