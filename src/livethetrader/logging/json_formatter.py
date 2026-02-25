from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
    def __init__(self, service_name: str = "livethetrader") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        event_data = getattr(record, "event_data", {})
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if isinstance(event_data, dict):
            payload.update(event_data)
        return json.dumps(payload, ensure_ascii=False, default=str)
