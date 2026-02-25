from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from livethetrader.models import Candle, Tick

TIMEFRAME_MINUTES: dict[str, int] = {"1m": 1, "5m": 5, "15m": 15}


def floor_timeframe(ts: datetime, timeframe: str) -> datetime:
    minutes = TIMEFRAME_MINUTES[timeframe]
    minute = ts.minute - (ts.minute % minutes)
    return ts.astimezone(timezone.utc).replace(minute=minute, second=0, microsecond=0)


@dataclass(slots=True)
class _CandleState:
    open: float
    high: float
    low: float
    close: float
    volume: float
    start: datetime


class MultiTimeframeCandleBuilder:
    def __init__(self, symbol: str, timeframes: tuple[str, ...] = ("1m", "5m", "15m")):
        self.symbol = symbol
        self.timeframes = timeframes
        self._states: dict[str, _CandleState] = {}

    def update(self, tick: Tick) -> list[Candle]:
        closed: list[Candle] = []
        for timeframe in self.timeframes:
            bucket_start = floor_timeframe(tick.timestamp, timeframe)
            state = self._states.get(timeframe)
            if state is None:
                self._states[timeframe] = _CandleState(
                    open=tick.last,
                    high=tick.last,
                    low=tick.last,
                    close=tick.last,
                    volume=tick.volume,
                    start=bucket_start,
                )
                continue

            if state.start != bucket_start:
                closed.append(
                    Candle(
                        symbol=self.symbol,
                        timeframe=timeframe,
                        timestamp_open=state.start,
                        timestamp_close=state.start
                        + timedelta(minutes=TIMEFRAME_MINUTES[timeframe])
                        - timedelta(milliseconds=1),
                        open=state.open,
                        high=state.high,
                        low=state.low,
                        close=state.close,
                        volume=state.volume,
                    )
                )
                self._states[timeframe] = _CandleState(
                    open=tick.last,
                    high=tick.last,
                    low=tick.last,
                    close=tick.last,
                    volume=tick.volume,
                    start=bucket_start,
                )
            else:
                state.close = tick.last
                state.high = max(state.high, tick.last)
                state.low = min(state.low, tick.last)
                state.volume += tick.volume

        return closed
