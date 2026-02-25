from __future__ import annotations

from typing import Literal

Direction = Literal["CALL", "PUT", "NEUTRO"]


class MultiTimeframeStrategy:
    """15m regime + 5m confirmation + 1m timing."""

    def evaluate(
        self, features_by_tf: dict[str, dict[str, float]]
    ) -> tuple[Direction, float, list[str]]:
        required = {"1m", "5m", "15m"}
        if not required.issubset(features_by_tf):
            return "NEUTRO", 0.0, ["missing_timeframe_features"]

        f15 = features_by_tf["15m"]
        f5 = features_by_tf["5m"]
        f1 = features_by_tf["1m"]

        reasons: list[str] = []
        score = 0.5
        direction: Direction = "NEUTRO"

        regime_up = f15["ema_9"] > f15["ema_21"] and f15["macd_hist"] > 0
        regime_down = f15["ema_9"] < f15["ema_21"] and f15["macd_hist"] < 0

        if regime_up:
            direction = "CALL"
            score += 0.2
            reasons.append("regime_up_15m")
        elif regime_down:
            direction = "PUT"
            score += 0.2
            reasons.append("regime_down_15m")
        else:
            return "NEUTRO", 0.35, ["regime_unclear_15m"]

        if direction == "CALL" and f5["ema_9"] > f5["ema_21"] and f5["macd_hist"] > 0:
            score += 0.15
            reasons.append("confirmation_5m")
        elif direction == "PUT" and f5["ema_9"] < f5["ema_21"] and f5["macd_hist"] < 0:
            score += 0.15
            reasons.append("confirmation_5m")
        else:
            return "NEUTRO", 0.4, reasons + ["no_confirmation_5m"]

        if direction == "CALL" and 40 <= f1["rsi_14"] <= 65 and f1["macd_hist"] > -0.0001:
            score += 0.15
            reasons.append("timing_1m")
        elif direction == "PUT" and 35 <= f1["rsi_14"] <= 60 and f1["macd_hist"] < 0.0001:
            score += 0.15
            reasons.append("timing_1m")
        else:
            return "NEUTRO", 0.45, reasons + ["timing_not_ready_1m"]

        atr_ratio = f1["atr_14"] / max(f1["ema_21"], 1e-9)
        if atr_ratio < 0.00005:
            return "NEUTRO", 0.3, reasons + ["low_volatility_filter"]

        return direction, min(score, 0.99), reasons
