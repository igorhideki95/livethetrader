from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from livethetrader.dashboard import normalize_dashboard_payload


@dataclass(slots=True)
class CurrentSignal:
    direction: str = "NEUTRO"
    confidence: float = 0.0
    timestamp: str = ""


@dataclass(slots=True)
class CandlePoint:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    indicators: dict[str, float] | None = None
    signal: str | None = None


@dataclass(slots=True)
class HistoryTrade:
    time: str
    symbol: str
    signal: str
    confidence: float
    result: str
    pnl: float


@dataclass(slots=True)
class EquityPoint:
    time: str
    equity: float


@dataclass(slots=True)
class DashboardMetrics:
    win_rate: float = 0.0
    profit_factor: float = 0.0
    drawdown: float = 0.0
    trades: int = 0
    expectancy: float = 0.0
    equity_curve: list[EquityPoint] | None = None


@dataclass(slots=True)
class DashboardSnapshot:
    status: str
    updated_at: str
    current_signal: CurrentSignal
    candles: list[CandlePoint]
    history: list[HistoryTrade]
    metrics: DashboardMetrics


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_snapshot(payload: dict[str, Any]) -> DashboardSnapshot:
    normalized = normalize_dashboard_payload(payload)

    signal_raw = normalized.get("current_signal") or {}
    signal = CurrentSignal(
        direction=str(signal_raw.get("direction") or "NEUTRO"),
        confidence=_as_float(signal_raw.get("confidence")),
        timestamp=str(signal_raw.get("timestamp") or ""),
    )

    candles: list[CandlePoint] = []
    for item in normalized.get("candles") or []:
        candles.append(
            CandlePoint(
                time=str(item.get("time") or ""),
                open=_as_float(item.get("open")),
                high=_as_float(item.get("high")),
                low=_as_float(item.get("low")),
                close=_as_float(item.get("close")),
                volume=_as_float(item.get("volume")),
                indicators=item.get("indicators") or {},
                signal=item.get("signal"),
            )
        )

    history: list[HistoryTrade] = []
    for item in normalized.get("history") or []:
        history.append(
            HistoryTrade(
                time=str(item.get("time") or ""),
                symbol=str(item.get("symbol") or ""),
                signal=str(item.get("signal") or item.get("direction") or "NEUTRO"),
                confidence=_as_float(item.get("confidence")),
                result=str(item.get("result") or ""),
                pnl=_as_float(item.get("pnl")),
            )
        )

    metrics_raw = normalized.get("metrics") or {}
    equity_curve = [
        EquityPoint(time=str(p.get("time") or ""), equity=_as_float(p.get("equity")))
        for p in (metrics_raw.get("equity_curve") or [])
    ]

    metrics = DashboardMetrics(
        win_rate=_as_float(metrics_raw.get("win_rate")),
        profit_factor=_as_float(metrics_raw.get("profit_factor")),
        drawdown=_as_float(metrics_raw.get("drawdown")),
        trades=int(metrics_raw.get("trades_total") or metrics_raw.get("trades") or 0),
        expectancy=_as_float(metrics_raw.get("expectancy")),
        equity_curve=equity_curve,
    )

    snapshot = DashboardSnapshot(
        status=str(normalized.get("status") or "offline"),
        updated_at=str(normalized.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        current_signal=signal,
        candles=candles,
        history=history,
        metrics=metrics,
    )

    if snapshot.metrics.trades == 0 and snapshot.history:
        snapshot.metrics = derive_metrics_from_history(snapshot.history)

    return snapshot


def derive_metrics_from_history(history: list[HistoryTrade]) -> DashboardMetrics:
    if not history:
        return DashboardMetrics(equity_curve=[])

    wins = [trade.pnl for trade in history if trade.pnl > 0]
    losses = [trade.pnl for trade in history if trade.pnl < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    equity_curve: list[EquityPoint] = []
    for trade in history:
        cumulative += trade.pnl
        peak = max(peak, cumulative)
        drawdown = peak - cumulative
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append(EquityPoint(time=trade.time, equity=cumulative))

    trades_count = len(history)
    win_rate = len(wins) / trades_count if trades_count else 0.0
    expectancy = cumulative / trades_count if trades_count else 0.0

    return DashboardMetrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        drawdown=max_drawdown,
        trades=trades_count,
        expectancy=expectancy,
        equity_curve=equity_curve,
    )
