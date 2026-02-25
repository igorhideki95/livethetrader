from __future__ import annotations

from collections import deque
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


def build_local_dashboard_payload(signal_contract: dict, system_status: str = "ONLINE") -> dict:
    """Utility to expose current backend signal in dashboard format for local runs."""

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "symbol": signal_contract["symbol"],
        "timeframe": signal_contract["timeframe"],
        "last_signal": signal_contract["direction"],
        "confidence": signal_contract["confidence"],
        "system_status": system_status,
        "metrics": {
            "win_rate": 0.57,
            "profit_factor": 1.32,
            "drawdown": 0.08,
            "trades_total": 34,
        },
        "history": [
            {
                "signal_id": signal_contract["signal_id"],
                "symbol": signal_contract["symbol"],
                "timeframe": signal_contract["timeframe"],
                "direction": signal_contract["direction"],
                "confidence": signal_contract["confidence"],
                "timestamp_open": signal_contract.get("timestamp_open", now),
            }
        ],
    }
