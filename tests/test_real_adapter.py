from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import timezone
from itertools import islice
from typing import Any

from livethetrader.ingestion.real_adapter import ProviderConfig, RealTickSourceAdapter


def test_stream_parses_and_normalizes_tick_fields() -> None:
    config = ProviderConfig(
        provider_name="fake",
        symbol="EURUSD",
        endpoint="https://fake.local/ticks",
    )

    def fake_feed(_: ProviderConfig) -> Iterator[Any]:
        yield {
            "timestamp": "2025-01-01T12:00:00-03:00",
            "bid": "1.1010",
            "ask": "1.1012",
            "last": "1.1011",
            "volume": "15",
        }

    adapter = RealTickSourceAdapter(config=config, message_stream_factory=fake_feed)

    tick = next(adapter.stream())

    assert tick.symbol == "EURUSD"
    assert tick.timestamp.tzinfo == timezone.utc
    assert tick.timestamp.isoformat() == "2025-01-01T15:00:00+00:00"
    assert tick.bid == 1.1010
    assert tick.ask == 1.1012
    assert tick.last == 1.1011
    assert tick.volume == 15.0


def test_stream_reconnects_with_exponential_backoff(caplog) -> None:
    config = ProviderConfig(
        provider_name="fake",
        symbol="EURUSD",
        endpoint="https://fake.local/ticks",
        initial_backoff_seconds=0.1,
        max_backoff_seconds=1.0,
    )
    sleep_calls: list[float] = []
    attempts = {"count": 0}

    def fake_feed(_: ProviderConfig) -> Iterator[Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            yield {
                "timestamp": 1_735_740_000_000,
                "bid": 1.2,
                "ask": 1.3,
                "last": 1.25,
                "volume": 1,
            }
            raise RuntimeError("temporary disconnect")

        yield {
            "timestamp": 1_735_740_001,
            "bid": 1.21,
            "ask": 1.31,
            "last": 1.26,
            "volume": 2,
        }

    caplog.set_level(logging.INFO)
    adapter = RealTickSourceAdapter(
        config=config,
        message_stream_factory=fake_feed,
        sleep_fn=sleep_calls.append,
    )

    ticks = list(islice(adapter.stream(), 2))

    assert len(ticks) == 2
    assert attempts["count"] >= 2
    assert sleep_calls == [0.1]

    logs = [json.loads(record.message) for record in caplog.records]
    events = {entry["event"] for entry in logs}
    assert "connection_error" in events
    assert "connection_resume" in events


def test_stream_skips_invalid_messages(caplog) -> None:
    config = ProviderConfig(
        provider_name="fake",
        symbol="EURUSD",
        endpoint="https://fake.local/ticks",
    )

    def fake_feed(_: ProviderConfig) -> Iterator[Any]:
        yield "not-json"
        yield {"timestamp": "2025-01-01T00:00:00Z", "bid": 1.0, "ask": 1.1, "price": 1.05}

    caplog.set_level(logging.WARNING)
    adapter = RealTickSourceAdapter(config=config, message_stream_factory=fake_feed)

    tick = next(adapter.stream())

    assert tick.last == 1.05
    assert tick.volume == 0.0
    assert any("parse_error" in record.message for record in caplog.records)
