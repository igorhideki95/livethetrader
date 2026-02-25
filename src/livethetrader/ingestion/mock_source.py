from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from livethetrader.ingestion.base import TickSource
from livethetrader.models import Tick


class MockTickSource(TickSource):
    """Deterministic-like mock feed for tests and local development."""

    def __init__(self, symbol: str = "EURUSD", seed: int = 7, start_price: float = 1.0840):
        self.symbol = symbol
        self._rng = random.Random(seed)
        self._price = start_price

    def stream(self, count: int = 1200, start: datetime | None = None) -> Iterator[Tick]:
        ts = start or datetime.now(timezone.utc).replace(second=0, microsecond=0)
        for _ in range(count):
            drift = self._rng.uniform(-0.00018, 0.00018)
            self._price = max(0.0001, self._price + drift)
            spread = self._rng.uniform(0.00001, 0.00005)
            last = self._price
            bid = last - spread / 2
            ask = last + spread / 2
            volume = self._rng.uniform(10, 400)
            yield Tick(
                symbol=self.symbol,
                timestamp=ts,
                bid=bid,
                ask=ask,
                last=last,
                volume=volume,
            )
            ts += timedelta(seconds=1)
