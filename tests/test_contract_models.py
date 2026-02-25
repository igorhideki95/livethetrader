from __future__ import annotations

import re
from datetime import datetime, timezone

from livethetrader.models import Candle, FeatureVector, SCHEMA_VERSION, Tick, TradeOutcome

UTC_ISO_8601_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _assert_common_contract_fields(contract: dict, *, symbol: str, timeframe: str) -> None:
    assert contract["schema_version"] == SCHEMA_VERSION
    assert contract["symbol"] == symbol
    assert contract["timeframe"] == timeframe
    assert UTC_ISO_8601_Z.match(contract["timestamp_open"])
    assert UTC_ISO_8601_Z.match(contract["timestamp_close"])


def test_tick_to_contract_includes_required_fields() -> None:
    tick = Tick(
        symbol="EURUSD",
        timestamp=datetime(2026, 1, 15, 12, 34, 56, 120000, tzinfo=timezone.utc),
        bid=1.08421,
        ask=1.08424,
        last=1.08423,
        volume=1023,
    )

    contract = tick.to_contract()

    _assert_common_contract_fields(contract, symbol="EURUSD", timeframe="TICK")
    assert contract["timestamp_open"] == contract["timestamp_close"]
    assert contract["bid"] == 1.08421
    assert contract["ask"] == 1.08424
    assert contract["last"] == 1.08423
    assert contract["volume"] == 1023


def test_feature_vector_to_contract_includes_required_fields() -> None:
    feature_vector = FeatureVector(
        symbol="EURUSD",
        timeframe="1m",
        timestamp_open=datetime(2026, 1, 15, 12, 30, 0, tzinfo=timezone.utc),
        timestamp_close=datetime(2026, 1, 15, 12, 34, 59, 999000, tzinfo=timezone.utc),
        features={"rsi_14": 61.3, "returns_1": 0.00011},
        feature_set_id="core_v1",
        label_horizon="5m",
    )

    contract = feature_vector.to_contract()

    _assert_common_contract_fields(contract, symbol="EURUSD", timeframe="1m")
    assert contract["features"] == {"rsi_14": 61.3, "returns_1": 0.00011}
    assert contract["feature_set_id"] == "core_v1"
    assert contract["label_horizon"] == "5m"


def test_trade_outcome_to_contract_includes_required_fields() -> None:
    trade_outcome = TradeOutcome(
        trade_id="trd_20260115_123500_001",
        signal_id="sig_20260115_123500_eurusd_1m",
        symbol="EURUSD",
        timeframe="1m",
        timestamp_open=datetime(2026, 1, 15, 12, 35, 0, tzinfo=timezone.utc),
        timestamp_close=datetime(2026, 1, 15, 12, 39, 59, 999000, tzinfo=timezone.utc),
        entry_price=1.0843,
        exit_price=1.0846,
        direction="CALL",
        confidence=0.78,
        expiry="5m",
        result="WIN",
        pnl=85.0,
    )

    contract = trade_outcome.to_contract()

    _assert_common_contract_fields(contract, symbol="EURUSD", timeframe="1m")
    assert contract["trade_id"] == "trd_20260115_123500_001"
    assert contract["signal_id"] == "sig_20260115_123500_eurusd_1m"
    assert contract["entry_price"] == 1.0843
    assert contract["exit_price"] == 1.0846
    assert contract["direction"] == "CALL"
    assert contract["confidence"] == 0.78
    assert contract["expiry"] == "5m"
    assert contract["result"] == "WIN"
    assert contract["pnl"] == 85.0


def test_candle_contract_remains_aligned_with_required_fields() -> None:
    candle = Candle(
        symbol="EURUSD",
        timeframe="1m",
        timestamp_open=datetime(2026, 1, 15, 12, 34, 0, tzinfo=timezone.utc),
        timestamp_close=datetime(2026, 1, 15, 12, 34, 59, 999000, tzinfo=timezone.utc),
        open=1.0841,
        high=1.0845,
        low=1.0839,
        close=1.0843,
        volume=24891,
    )

    contract = candle.to_contract()

    _assert_common_contract_fields(contract, symbol="EURUSD", timeframe="1m")
    assert contract["open"] == 1.0841
    assert contract["high"] == 1.0845
    assert contract["low"] == 1.0839
    assert contract["close"] == 1.0843
    assert contract["volume"] == 24891
