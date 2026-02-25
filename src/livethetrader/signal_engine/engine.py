from __future__ import annotations

from datetime import datetime, timezone

from livethetrader.models import Signal
from livethetrader.risk.manager import RiskManager
from livethetrader.strategy.mtf_strategy import MultiTimeframeStrategy


class SignalEngine:
    def __init__(self, strategy: MultiTimeframeStrategy | None = None, risk: RiskManager | None = None):
        self.strategy = strategy or MultiTimeframeStrategy()
        self.risk = risk or RiskManager()

    def generate(self, symbol: str, features_by_tf: dict[str, dict[str, float]], expiry: str = "5m") -> Signal:
        direction, confidence, reasons = self.strategy.evaluate(features_by_tf)
        direction, confidence, risk_reasons = self.risk.approve(direction, confidence)
        reason_codes = reasons + risk_reasons
        return Signal(
            symbol=symbol,
            timeframe="1m",
            timestamp_open=datetime.now(timezone.utc),
            direction=direction,
            confidence=confidence,
            expiry=expiry,
            reason_codes=reason_codes,
        )
