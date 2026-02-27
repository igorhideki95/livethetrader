from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal, cast

from livethetrader.api.service import TradingSignalService
from livethetrader.dashboard.contract import DASHBOARD_SCHEMA_VERSION
from livethetrader.ui.models import (
    CandlePoint,
    CurrentSignal,
    DashboardMetrics,
    DashboardSnapshot,
    EquityPoint,
    HistoryTrade,
)

ControlAction = Literal["start", "pause", "restart", "reload-config"]


class DashboardState:
    def __init__(self, symbol: str = "EURUSD", timeframe: str = "1m") -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.status = "paused"
        self.updated_at = ""
        self.current_signal = CurrentSignal()
        self.candles: list[CandlePoint] = []
        self.history: list[HistoryTrade] = []
        self.metrics = DashboardMetrics(equity_curve=[])
        self._equity = 0.0
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self.status = "paused"
            self.updated_at = ""
            self.current_signal = CurrentSignal()
            self.candles = []
            self.history = []
            self.metrics = DashboardMetrics(equity_curve=[])
            self._equity = 0.0

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status
            self.updated_at = _utc_now()

    def apply_signal(self, signal: dict) -> None:
        ts = str(signal.get("timestamp_open") or _utc_now())
        direction = str(signal.get("direction") or "NEUTRO")
        confidence = float(signal.get("confidence") or 0.0)

        candle = CandlePoint(
            time=ts,
            open=1.1020,
            high=1.1030,
            low=1.1010,
            close=1.1025,
            volume=100.0,
            indicators={"confidence": confidence},
            signal=direction,
        )

        pnl = _derive_pnl(direction=direction, confidence=confidence)
        trade = HistoryTrade(
            time=ts,
            symbol=str(signal.get("symbol") or self.symbol),
            signal=direction,
            confidence=confidence,
            result="OPEN" if direction == "NEUTRO" else ("WIN" if pnl > 0 else "LOSS"),
            pnl=pnl,
        )

        with self._lock:
            self.updated_at = _utc_now()
            self.current_signal = CurrentSignal(
                direction=direction,
                confidence=confidence,
                timestamp=ts,
            )
            self.candles = [*self.candles[-49:], candle]
            self.history = [*self.history[-99:], trade]
            self._equity += pnl
            self.metrics = _build_metrics(self.history, self._equity)

    def to_payload(self) -> dict:
        with self._lock:
            metrics_payload = asdict(self.metrics)
            trades_total = int(metrics_payload.get("trades") or 0)
            snapshot = DashboardSnapshot(
                schema_version=DASHBOARD_SCHEMA_VERSION,
                symbol=self.symbol,
                timeframe=self.timeframe,
                system_status=self.status.upper(),
                status=self.status,
                updated_at=self.updated_at or _utc_now(),
                current_signal=self.current_signal,
                candles=list(self.candles),
                history=list(self.history),
                metrics=self.metrics,
            )
            payload = asdict(snapshot)
            payload["metrics"] = {
                **metrics_payload,
                "trades_total": trades_total,
                "trades": trades_total,
            }
        return payload


class DashboardProcessingLoop:
    def __init__(
        self,
        state: DashboardState,
        service: TradingSignalService,
        tick_count: int = 300,
        cycle_interval: float = 0.2,
    ) -> None:
        self.state = state
        self.service = service
        self._service_lock = threading.Lock()
        self.tick_count = tick_count
        self.cycle_interval = cycle_interval
        self._running = threading.Event()
        self._stopped = threading.Event()
        self._stopped.clear()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def control(self, action: ControlAction) -> str:
        if action == "reload-config":
            with self._service_lock:
                self.service = TradingSignalService(symbol=self.state.symbol)
            return "Configuração recarregada."

        if action == "start":
            self._running.set()
            self.state.set_status("running")
            return "Sistema iniciado."
        if action == "pause":
            self._running.clear()
            self.state.set_status("paused")
            return "Sistema pausado."

        self._running.clear()
        self.state.reset()
        self._running.set()
        self.state.set_status("running")
        return "Sistema reiniciado."

    def shutdown(self) -> None:
        self._running.clear()
        self._stopped.set()
        self._worker.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stopped.is_set():
            if not self._running.wait(timeout=0.1):
                continue

            with self._service_lock:
                active_service = self.service
            signal = active_service.run_once(tick_count=self.tick_count)
            self.state.apply_signal(signal)
            time.sleep(self.cycle_interval)


def create_dashboard_http_server(
    host: str,
    port: int,
    tick_count: int = 300,
    cycle_interval: float = 0.2,
) -> ThreadingHTTPServer:
    state = DashboardState()
    loop = DashboardProcessingLoop(
        state=state,
        service=TradingSignalService(symbol=state.symbol),
        tick_count=tick_count,
        cycle_interval=cycle_interval,
    )

    class _DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/api/v1/dashboard":
                self.send_response(404)
                self.end_headers()
                return
            self._send_json(200, state.to_payload())

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.startswith("/api/v1/dashboard/control/"):
                self.send_response(404)
                self.end_headers()
                return

            action = self.path.rsplit("/", 1)[-1]
            if action not in {"start", "pause", "restart", "reload-config"}:
                self._send_json(404, {"ok": False, "message": f"Ação não suportada: {action}"})
                return

            message = loop.control(action)  # type: ignore[arg-type]
            self._send_json(
                200,
                {"ok": True, "message": message, "status": state.to_payload()["status"]},
            )

        def _send_json(self, status_code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), _DashboardHandler)
    server.dashboard_loop = loop  # type: ignore[attr-defined]
    return server


def shutdown_dashboard_http_server(server: ThreadingHTTPServer) -> None:
    loop = getattr(server, "dashboard_loop", None)
    if loop:
        loop.shutdown()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _derive_pnl(direction: str, confidence: float) -> float:
    if direction == "NEUTRO":
        return 0.0
    return round((confidence - 0.5) * 100, 2)


def _build_metrics(history: list[HistoryTrade], equity: float) -> DashboardMetrics:
    if not history:
        return DashboardMetrics(equity_curve=[])

    closed = [item for item in history if item.signal != "NEUTRO"]
    wins = [item.pnl for item in closed if item.pnl > 0]
    losses = [item.pnl for item in closed if item.pnl < 0]
    gross_loss = abs(sum(losses))

    win_rate = len(wins) / len(closed) if closed else 0.0
    profit_factor = sum(wins) / gross_loss if gross_loss else 0.0
    expectancy = equity / len(closed) if closed else 0.0

    running = 0.0
    peak = 0.0
    max_drawdown = 0.0
    equity_curve: list[EquityPoint] = []
    for item in history:
        running += item.pnl
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)
        equity_curve.append(EquityPoint(time=item.time, equity=running))

    return DashboardMetrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        drawdown=max_drawdown,
        trades=len(history),
        expectancy=expectancy,
        equity_curve=equity_curve,
    )
