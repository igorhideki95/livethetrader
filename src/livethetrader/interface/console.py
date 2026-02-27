from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, TextIO

from livethetrader.api.service import TradingSignalService
from livethetrader.config import load_config
from livethetrader.interface.client import BackendPollingClient
from livethetrader.interface.models import DashboardSnapshot
from livethetrader.interface.service import InterfaceService, build_local_dashboard_payload
from livethetrader.logging import configure_logging, get_logger, log_event

LOGGER = get_logger(__name__)

_CONTROL_MESSAGES = {
    "start": "Sistema iniciado.",
    "pause": "Sistema pausado.",
    "restart": "Sistema reiniciado.",
    "reload-config": "Configuração recarregada.",
}


class _LocalDashboardHandler(BaseHTTPRequestHandler):
    service = TradingSignalService(symbol="EURUSD")

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/api/v1/dashboard":
            self.send_response(404)
            self.end_headers()
            return

        signal = self.service.run_once(tick_count=6000)
        payload = build_local_dashboard_payload(signal_contract=signal)
        self._send_json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/v1/dashboard/control/"):
            self.send_response(404)
            self.end_headers()
            return

        action = self.path.rsplit("/", 1)[-1]
        if action not in _CONTROL_MESSAGES:
            payload = {"ok": False, "message": f"Ação não suportada: {action}"}
            self._send_json(404, payload)
            return

        payload = {"ok": True, "message": _CONTROL_MESSAGES[action]}
        self._send_json(200, payload)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
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


def _print_terminal_snapshot(snapshot: DashboardSnapshot, output_stream: TextIO) -> None:
    output_stream.write("\033[2J\033[H")
    output_stream.write(render_snapshot(snapshot))
    output_stream.write("\n")
    output_stream.flush()


def run_interface(
    base_url: str,
    interval: float = 2.0,
    *,
    render_terminal: bool = True,
    output_stream: TextIO | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    interface_service: InterfaceService | None = None,
    max_iterations: int | None = None,
) -> None:
    interface = interface_service or InterfaceService(client=BackendPollingClient(base_url=base_url))
    stream = output_stream or sys.stdout
    iterations = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        snapshot, error = interface.fetch_snapshot()
        if error:
            log_event(LOGGER, "interface_loop_error", level=40, error=error)
            sleep_fn(interval)
            iterations += 1
            continue

        if snapshot:
            log_event(
                LOGGER,
                "interface_snapshot_received",
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                last_signal=snapshot.last_signal,
                confidence=snapshot.confidence,
                status=snapshot.system_status,
            )
            if render_terminal:
                _print_terminal_snapshot(snapshot=snapshot, output_stream=stream)
        sleep_fn(interval)
        iterations += 1


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
    parser.add_argument(
        "--log-only",
        action="store_true",
        help="Desativa dashboard ANSI no terminal e mantém apenas logs estruturados.",
    )
    parser.add_argument(
        "--terminal-dashboard",
        action="store_true",
        help="Força renderização do dashboard ANSI no terminal.",
    )
    args = parser.parse_args()

    render_terminal = True
    if args.log_only:
        render_terminal = False
    if args.terminal_dashboard:
        render_terminal = True

    server = None
    try:
        if args.local_backend:
            server = _start_local_server(args.backend_port)
            args.base_url = f"http://127.0.0.1:{args.backend_port}"
            log_event(LOGGER, "local_backend_started", base_url=args.base_url)
        run_interface(base_url=args.base_url, interval=args.poll_interval, render_terminal=render_terminal)
    finally:
        if server:
            server.shutdown()
            log_event(LOGGER, "local_backend_shutdown")


if __name__ == "__main__":
    main()
