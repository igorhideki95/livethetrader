from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass(slots=True)
class SignalHistoryItem:
    signal_id: str
    symbol: str
    timeframe: str
    direction: str
    confidence: float
    timestamp_open: datetime

    @classmethod
    def from_payload(cls, payload: dict) -> "SignalHistoryItem":
        return cls(
            signal_id=payload["signal_id"],
            symbol=payload["symbol"],
            timeframe=payload["timeframe"],
            direction=payload["direction"],
            confidence=float(payload["confidence"]),
            timestamp_open=_parse_datetime(payload["timestamp_open"]),
        )


@dataclass(slots=True)
class SystemMetrics:
    win_rate: float
    profit_factor: float
    drawdown: float
    trades_total: int

    @classmethod
    def from_payload(cls, payload: dict) -> "SystemMetrics":
        return cls(
            win_rate=float(payload.get("win_rate", 0.0)),
            profit_factor=float(payload.get("profit_factor", 0.0)),
            drawdown=float(payload.get("drawdown", 0.0)),
            trades_total=int(payload.get("trades_total", payload.get("trades", 0))),
        )


@dataclass(slots=True)
class DashboardSnapshot:
    symbol: str
    timeframe: str
    last_signal: str
    confidence: float
    system_status: str
    metrics: SystemMetrics
    history: list[SignalHistoryItem] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict) -> "DashboardSnapshot":
        if "status" in payload and "current_signal" in payload:
            return cls._from_ui_payload(payload)
        return cls._from_legacy_payload(payload)

    @classmethod
    def _from_legacy_payload(cls, payload: dict) -> "DashboardSnapshot":
        metrics = SystemMetrics.from_payload(payload.get("metrics", {}))
        history = [SignalHistoryItem.from_payload(item) for item in payload.get("history", [])]
        return cls(
            symbol=payload["symbol"],
            timeframe=payload["timeframe"],
            last_signal=payload["last_signal"],
            confidence=float(payload["confidence"]),
            system_status=payload.get("system_status", "UNKNOWN"),
            metrics=metrics,
            history=history,
        )

    @classmethod
    def _from_ui_payload(cls, payload: dict) -> "DashboardSnapshot":
        current_signal = payload.get("current_signal") or {}
        history_items = payload.get("history") or []
        symbol = str(history_items[-1].get("symbol", "UNKNOWN")) if history_items else "UNKNOWN"
        metrics_payload = payload.get("metrics") or {}

        metrics = SystemMetrics(
            win_rate=float(metrics_payload.get("win_rate", 0.0)),
            profit_factor=float(metrics_payload.get("profit_factor", 0.0)),
            drawdown=float(metrics_payload.get("drawdown", 0.0)),
            trades_total=int(metrics_payload.get("trades", len(history_items))),
        )
        history = [
            SignalHistoryItem(
                signal_id=f"hist_{index}",
                symbol=str(item.get("symbol", symbol)),
                timeframe="unknown",
                direction=str(item.get("signal", "NEUTRO")),
                confidence=float(item.get("confidence", 0.0)),
                timestamp_open=_parse_datetime(str(item.get("time", datetime.now(timezone.utc).isoformat()))),
            )
            for index, item in enumerate(history_items)
        ]

        return cls(
            symbol=symbol,
            timeframe="unknown",
            last_signal=str(current_signal.get("direction", "NEUTRO")),
            confidence=float(current_signal.get("confidence", 0.0)),
            system_status=str(payload.get("status", "UNKNOWN")).upper(),
            metrics=metrics,
            history=history,
        )
