from __future__ import annotations

from livethetrader.models import Direction


class RiskManager:
    def __init__(
        self,
        min_confidence: float = 0.6,
        rejection_confidence_max: float = 0.45,
    ) -> None:
        self.min_confidence = min_confidence
        self.rejection_confidence_max = rejection_confidence_max

    def approve(
        self, direction: Direction, confidence: float
    ) -> tuple[Direction, float, list[str]]:
        if direction == "NEUTRO":
            return direction, confidence, ["neutral_signal"]
        if confidence <= self.rejection_confidence_max:
            return "NEUTRO", confidence, ["confidence_below_rejection_threshold"]
        if confidence < self.min_confidence:
            return "NEUTRO", confidence, ["confidence_below_threshold"]
        return direction, confidence, ["risk_ok"]
