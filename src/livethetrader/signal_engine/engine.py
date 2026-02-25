from __future__ import annotations

from datetime import datetime, timezone

from livethetrader.ml import SignalPublicationGate
from livethetrader.models import Signal
from livethetrader.risk.manager import RiskManager
from livethetrader.strategy.mtf_strategy import MultiTimeframeStrategy


class SignalEngine:
    def __init__(
        self,
        strategy: MultiTimeframeStrategy | None = None,
        risk: RiskManager | None = None,
        publication_gate: SignalPublicationGate | None = None,
    ):
        self.strategy = strategy or MultiTimeframeStrategy()
        self.risk = risk or RiskManager()
        self.publication_gate = publication_gate or SignalPublicationGate()

    def generate(
        self, symbol: str, features_by_tf: dict[str, dict[str, float]], expiry: str = "5m"
    ) -> Signal:
        strategy_direction, confidence, reasons = self.strategy.evaluate(features_by_tf)
        risk_direction, risk_confidence, risk_reasons = self.risk.approve(
            strategy_direction, confidence
        )

        features_1m = features_by_tf.get("1m", {})
        direction, confidence, ml_reasons = self.publication_gate.approve(
            strategy_direction=strategy_direction,
            risk_direction=risk_direction,
            confidence=risk_confidence,
            features=features_1m,
        )
        reason_codes = reasons + risk_reasons + ml_reasons
        return Signal(
            symbol=symbol,
            timeframe="1m",
            timestamp_open=datetime.now(timezone.utc),
            direction=direction,
            confidence=confidence,
            expiry=expiry,
            reason_codes=reason_codes,
        )
