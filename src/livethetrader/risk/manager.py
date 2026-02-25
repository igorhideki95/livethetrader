from __future__ import annotations


class RiskManager:
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence

    def approve(self, direction: str, confidence: float) -> tuple[str, float, list[str]]:
        if direction == "NEUTRO":
            return direction, confidence, ["neutral_signal"]
        if confidence < self.min_confidence:
            return "NEUTRO", confidence, ["confidence_below_threshold"]
        return direction, confidence, ["risk_ok"]
