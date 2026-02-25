from __future__ import annotations

from collections import deque
from typing import Any
from datetime import datetime, timezone

from livethetrader.interface.client import BackendPollingClient, PollResult
from livethetrader.interface.models import DashboardSnapshot
from livethetrader.logging import get_logger, log_event

LOGGER = get_logger(__name__)


class InterfaceService:
    """Transforms backend responses into dashboard snapshots."""

    def __init__(self, client: BackendPollingClient, history_limit: int = 20) -> None:
        self.client = client
        self.history_limit = history_limit
        self._history: deque[dict] = deque(maxlen=history_limit)

    def fetch_snapshot(self) -> tuple[DashboardSnapshot | None, str | None]:
        result: PollResult = self.client.poll_once()
        if not result.connected or not result.payload:
            error_message = result.error or "Backend indisponível"
            log_event(LOGGER, "interface_snapshot_error", error=error_message)
            return None, error_message

        payload = result.payload
        payload_history = payload.get("history", [])
        self._history.extend(payload_history)
        payload["history"] = list(self._history)
        snapshot = DashboardSnapshot.from_payload(payload)
        log_event(
            LOGGER,
            "interface_snapshot_ready",
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            history_count=len(snapshot.history),
        )
        return snapshot, None


def build_local_dashboard_payload(signal_contract: dict[str, Any], system_status: str = "running") -> dict[str, Any]:
    """Utility to expose current backend signal in canonical dashboard format for local runs."""

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    direction = str(signal_contract.get("direction", "NEUTRO"))
    confidence = float(signal_contract.get("confidence", 0.0))
    symbol = str(signal_contract.get("symbol", "UNKNOWN"))

    history = [
        {
            "time": str(signal_contract.get("timestamp_open", now)),
            "symbol": symbol,
            "signal": direction,
            "confidence": confidence,
            "result": "OPEN",
            "pnl": 0.0,
        }
    ]

    return {
        "status": system_status.lower(),
        "updated_at": now,
        "current_signal": {
            "direction": direction,
            "confidence": confidence,
            "timestamp": str(signal_contract.get("timestamp_open", now)),
        },
        "candles": [
            {
                "time": now,
                "open": 1.1020,
                "high": 1.1030,
                "low": 1.1010,
                "close": 1.1025,
                "volume": 100.0,
                "indicators": {
                    "ema_9": 1.1022,
                    "ema_21": 1.1019,
                },
                "signal": direction,
            }
        ],
        "history": history,
        "metrics": {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "drawdown": 0.0,
            "trades": len(history),
            "expectancy": 0.0,
            "equity_curve": [
                {
                    "time": history[0]["time"],
                    "equity": 0.0,
                }
            ],
        },
    }
