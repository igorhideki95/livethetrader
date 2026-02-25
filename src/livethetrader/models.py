from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import uuid4

SCHEMA_VERSION = "1.0.0"
Direction = Literal["CALL", "PUT", "NEUTRO"]
TradeDirection = Literal["CALL", "PUT"]
TradeResult = Literal["WIN", "LOSS", "DRAW"]


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

    def to_contract(self) -> dict:
        timestamp = to_utc_iso(self.timestamp)
        return {
            "schema_version": SCHEMA_VERSION,
            "symbol": self.symbol,
            "timeframe": "TICK",
            "timestamp_open": timestamp,
            "timestamp_close": timestamp,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "volume": self.volume,
        }


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


@dataclass(slots=True)
class FeatureVector:
    symbol: str
    timeframe: str
    timestamp_open: datetime
    timestamp_close: datetime
    features: dict[str, float]
    feature_set_id: str
    label_horizon: str

    def to_contract(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp_open": to_utc_iso(self.timestamp_open),
            "timestamp_close": to_utc_iso(self.timestamp_close),
            "features": {name: float(value) for name, value in self.features.items()},
            "feature_set_id": self.feature_set_id,
            "label_horizon": self.label_horizon,
        }


@dataclass(slots=True)
class TradeOutcome:
    trade_id: str
    signal_id: str
    symbol: str
    timeframe: str
    timestamp_open: datetime
    timestamp_close: datetime
    entry_price: float
    exit_price: float
    direction: TradeDirection
    confidence: float
    expiry: str
    result: TradeResult
    pnl: float

    def to_contract(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "trade_id": self.trade_id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp_open": to_utc_iso(self.timestamp_open),
            "timestamp_close": to_utc_iso(self.timestamp_close),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "direction": self.direction,
            "confidence": round(min(max(self.confidence, 0.0), 1.0), 4),
            "expiry": self.expiry,
            "result": self.result,
            "pnl": self.pnl,
        }
