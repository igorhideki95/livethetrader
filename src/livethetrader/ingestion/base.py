from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from livethetrader.models import Tick


class TickSource(ABC):
    """Contract for any tick feed provider."""

    @abstractmethod
    def stream(self) -> Iterator[Tick]:
        """Yield market ticks."""
