from __future__ import annotations

from datetime import datetime, timezone

from livethetrader.config import AppConfig, load_config
from livethetrader.logging import get_logger, log_event
from livethetrader.ml import SignalPublicationGate
from livethetrader.models import Signal
from livethetrader.risk.manager import RiskManager
from livethetrader.strategy.mtf_strategy import MultiTimeframeStrategy

LOGGER = get_logger(__name__)


class SignalEngine:
    def __init__(
        self,
        publication_gate: SignalPublicationGate,
        strategy: MultiTimeframeStrategy | None = None,
        risk: RiskManager | None = None,
        config: AppConfig | None = None,
    ):
        self.strategy = strategy or MultiTimeframeStrategy()
        self.risk = risk or RiskManager()
        self.publication_gate = publication_gate
        self.config = config or load_config()

    def generate(
        self, symbol: str, features_by_tf: dict[str, dict[str, float]], expiry: str = "5m"
    ) -> Signal:
        strategy_direction, confidence, reasons = self.strategy.evaluate(features_by_tf)
        risk_direction, _risk_confidence, risk_reasons = self.risk.approve(
            strategy_direction, confidence
        )

        features_1m = features_by_tf.get("1m", {})
        direction, confidence, ml_reasons = self.publication_gate.approve(
            strategy_direction=strategy_direction,
            risk_direction=risk_direction,
            features=features_1m,
        )
        reason_codes = reasons + risk_reasons + ml_reasons

        if confidence < self.config.thresholds.confidence_min:
            log_event(
                LOGGER,
                "signal_confidence_below_threshold",
                symbol=symbol,
                confidence=confidence,
                threshold=self.config.thresholds.confidence_min,
            )

        log_event(
            LOGGER,
            "signal_generated",
            symbol=symbol,
            direction=direction,
            strategy_direction=strategy_direction,
            risk_direction=risk_direction,
            confidence=confidence,
            reason_codes=reason_codes,
        )

        return Signal(
            symbol=symbol,
            timeframe="1m",
            timestamp_open=datetime.now(timezone.utc),
            direction=direction,
            confidence=confidence,
            expiry=expiry,
            reason_codes=reason_codes,
        )
