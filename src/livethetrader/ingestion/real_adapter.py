from __future__ import annotations

from collections.abc import Iterator

from livethetrader.ingestion.base import TickSource
from livethetrader.models import Tick


class RealTickSourceAdapter(TickSource):
    """Placeholder adapter for broker/exchange integrations."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def stream(self) -> Iterator[Tick]:
        raise NotImplementedError(
            f"Provider '{self.provider_name}' not configured yet. "
            "Implement API/websocket connection here."
        )
