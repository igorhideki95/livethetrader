from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

DASHBOARD_SCHEMA_VERSION = "1.0.0"
_REQUIRED_FIELDS = ("schema_version", "status", "updated_at", "current_signal", "metrics")


@dataclass(slots=True)
class DashboardContractError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_dashboard_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "status" in payload and "current_signal" in payload:
        normalized = _normalize_ui_payload(payload)
    else:
        normalized = _normalize_legacy_payload(payload)

    _validate_dashboard_payload(normalized)
    return normalized


def _normalize_ui_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    now = _utc_now_iso()
    status = str(payload.get("status") or "offline").lower()
    updated_at = str(payload.get("updated_at") or now)

    current_signal_raw = payload.get("current_signal") or {}
    current_signal = {
        "direction": str(current_signal_raw.get("direction") or "NEUTRO"),
        "confidence": _as_float(current_signal_raw.get("confidence")),
        "timestamp": str(current_signal_raw.get("timestamp") or updated_at),
    }

    history: list[dict[str, Any]] = []
    for index, item in enumerate(payload.get("history") or []):
        time_value = str(item.get("time") or updated_at)
        symbol = str(item.get("symbol") or payload.get("symbol") or "UNKNOWN")
        direction = str(item.get("signal") or "NEUTRO")
        history.append(
            {
                "signal_id": str(item.get("signal_id") or f"hist_{index}"),
                "symbol": symbol,
                "timeframe": str(item.get("timeframe") or payload.get("timeframe") or "unknown"),
                "direction": direction,
                "confidence": _as_float(item.get("confidence")),
                "timestamp_open": time_value,
                "time": time_value,
                "signal": direction,
                "result": str(item.get("result") or ""),
                "pnl": _as_float(item.get("pnl")),
            }
        )

    symbol = str(payload.get("symbol") or (history[-1]["symbol"] if history else "UNKNOWN"))
    timeframe = str(
        payload.get("timeframe") or (history[-1]["timeframe"] if history else "unknown")
    )

    metrics_raw = payload.get("metrics") or {}
    trades_total = _as_int(metrics_raw.get("trades_total"), _as_int(metrics_raw.get("trades"), 0))
    metrics = {
        "win_rate": _as_float(metrics_raw.get("win_rate")),
        "profit_factor": _as_float(metrics_raw.get("profit_factor")),
        "drawdown": _as_float(metrics_raw.get("drawdown")),
        "trades_total": trades_total,
        "trades": trades_total,
        "expectancy": _as_float(metrics_raw.get("expectancy")),
        "equity_curve": list(metrics_raw.get("equity_curve") or []),
    }

    return {
        "schema_version": str(payload.get("schema_version") or DASHBOARD_SCHEMA_VERSION),
        "status": status,
        "system_status": str(payload.get("system_status") or status).upper(),
        "updated_at": updated_at,
        "symbol": symbol,
        "timeframe": timeframe,
        "current_signal": current_signal,
        "last_signal": current_signal["direction"],
        "confidence": current_signal["confidence"],
        "candles": list(payload.get("candles") or []),
        "history": history,
        "metrics": metrics,
    }


def _normalize_legacy_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    now = _utc_now_iso()
    history: list[dict[str, Any]] = []
    for item in payload.get("history") or []:
        timestamp = str(item.get("timestamp_open") or now)
        direction = str(item.get("direction") or item.get("signal") or "NEUTRO")
        history.append(
            {
                "signal_id": str(item.get("signal_id") or ""),
                "symbol": str(item.get("symbol") or payload.get("symbol") or "UNKNOWN"),
                "timeframe": str(item.get("timeframe") or payload.get("timeframe") or "unknown"),
                "direction": direction,
                "confidence": _as_float(item.get("confidence")),
                "timestamp_open": timestamp,
                "time": str(item.get("time") or timestamp),
                "signal": direction,
                "result": str(item.get("result") or ""),
                "pnl": _as_float(item.get("pnl")),
            }
        )

    status = str(payload.get("status") or payload.get("system_status") or "offline").lower()
    updated_at = str(payload.get("updated_at") or now)
    confidence = _as_float(payload.get("confidence"))
    direction = str(payload.get("last_signal") or "NEUTRO")

    metrics_raw = payload.get("metrics") or {}
    trades_total = _as_int(metrics_raw.get("trades_total"), _as_int(metrics_raw.get("trades"), 0))

    return {
        "schema_version": str(payload.get("schema_version") or DASHBOARD_SCHEMA_VERSION),
        "status": status,
        "system_status": str(payload.get("system_status") or status).upper(),
        "updated_at": updated_at,
        "symbol": str(payload.get("symbol") or "UNKNOWN"),
        "timeframe": str(payload.get("timeframe") or "unknown"),
        "current_signal": {
            "direction": direction,
            "confidence": confidence,
            "timestamp": str(payload.get("timestamp_open") or updated_at),
        },
        "last_signal": direction,
        "confidence": confidence,
        "candles": list(payload.get("candles") or []),
        "history": history,
        "metrics": {
            "win_rate": _as_float(metrics_raw.get("win_rate")),
            "profit_factor": _as_float(metrics_raw.get("profit_factor")),
            "drawdown": _as_float(metrics_raw.get("drawdown")),
            "trades_total": trades_total,
            "trades": trades_total,
            "expectancy": _as_float(metrics_raw.get("expectancy")),
            "equity_curve": list(metrics_raw.get("equity_curve") or []),
        },
    }


def _validate_dashboard_payload(payload: Mapping[str, Any]) -> None:
    missing = [field for field in _REQUIRED_FIELDS if field not in payload]
    if missing:
        raise DashboardContractError(
            f"DashboardSnapshot inválido: campos obrigatórios ausentes: {missing}"
        )

    if str(payload.get("schema_version") or "") != DASHBOARD_SCHEMA_VERSION:
        raise DashboardContractError(
            "DashboardSnapshot inválido: schema_version não suportada "
            f"({payload.get('schema_version')!r})"
        )

    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping) or "trades_total" not in metrics:
        raise DashboardContractError(
            "DashboardSnapshot inválido: metrics.trades_total é obrigatório"
        )
