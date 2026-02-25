from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import uuid4

SCHEMA_VERSION = "1.0.0"
Direction = Literal["CALL", "PUT", "NEUTRO"]


def to_utc_iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Tick:
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: float


@dataclass(slots=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp_open: datetime
    timestamp_close: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_contract(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp_open": to_utc_iso(self.timestamp_open),
            "timestamp_close": to_utc_iso(self.timestamp_close),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(slots=True)
class Signal:
    symbol: str
    timeframe: str
    timestamp_open: datetime
    direction: Direction
    confidence: float
    expiry: str
    reason_codes: list[str] = field(default_factory=list)
    signal_id: str = field(default_factory=lambda: f"sig_{uuid4().hex[:12]}")

    @property
    def timestamp_close(self) -> datetime:
        minutes = int(self.expiry.rstrip("m"))
        return self.timestamp_open + timedelta(minutes=minutes)

    def to_contract(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp_open": to_utc_iso(self.timestamp_open),
            "timestamp_close": to_utc_iso(self.timestamp_close),
            "direction": self.direction,
            "confidence": round(min(max(self.confidence, 0.0), 1.0), 4),
            "expiry": self.expiry,
            "reason_codes": self.reason_codes,
        }
