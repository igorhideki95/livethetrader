from __future__ import annotations

from collections import defaultdict

from livethetrader.indicators.core import atr, ema, macd, rsi
from livethetrader.models import Candle


class IndicatorService:
    def __init__(self) -> None:
        self._candles: dict[str, list[Candle]] = defaultdict(list)

    def push(self, candle: Candle) -> dict[str, float] | None:
        candles = self._candles[candle.timeframe]
        candles.append(candle)
        if len(candles) > 400:
            del candles[:-400]

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        features = {
            "ema_9": ema(closes, 9),
            "ema_21": ema(closes, 21),
            "rsi_14": rsi(closes, 14),
            "atr_14": atr(highs, lows, closes, 14),
        }
        macd_values = macd(closes)
        if macd_values is not None:
            features.update(
                {
                    "macd": macd_values["macd"],
                    "macd_signal": macd_values["signal"],
                    "macd_hist": macd_values["histogram"],
                }
            )

        if any(value is None for value in features.values()):
            return None
        return {key: float(value) for key, value in features.items() if value is not None}
