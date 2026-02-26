from __future__ import annotations

import json
import logging
from io import StringIO

from livethetrader.config import load_config
from livethetrader.logging import JsonLogFormatter, configure_logging, get_logger, log_event


def test_load_config_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LTT_SYMBOLS", "EURUSD,GBPUSD")
    monkeypatch.setenv("LTT_TIMEFRAMES", "1m,5m")
    monkeypatch.setenv("LTT_MAX_TICKS_PER_RUN", "1200")
    monkeypatch.setenv("LTT_CONFIDENCE_MIN", "0.72")
    monkeypatch.setenv("LTT_RISK_REJECTION_MAX", "0.51")
    monkeypatch.setenv("LTT_LOG_LEVEL", "debug")

    config = load_config()

    assert config.symbols == ["EURUSD", "GBPUSD"]
    assert config.timeframes == ["1m", "5m"]
    assert config.limits.max_ticks_per_run == 1200
    assert config.thresholds.confidence_min == 0.72
    assert config.thresholds.risk_rejection_max == 0.51
    assert config.logging.level == "DEBUG"


def test_load_config_log_service_name_override(monkeypatch) -> None:
    monkeypatch.setenv("LTT_LOG_SERVICE_NAME", "livethetrader-custom")

    config = load_config()

    assert config.logging.service_name == "livethetrader-custom"


def test_json_logging_format_is_structured() -> None:
    configure_logging(level="INFO", service_name="livethetrader-ci")
    logger = get_logger("tests.logging")

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter(service_name="livethetrader-ci"))
    logger.addHandler(handler)

    try:
        log_event(logger, "evidence_event", symbol="EURUSD", value=1)
    finally:
        logger.removeHandler(handler)

    parsed = json.loads(stream.getvalue().strip())
    assert parsed["service"] == "livethetrader-ci"
    assert parsed["event"] == "evidence_event"
    assert parsed["symbol"] == "EURUSD"
    assert parsed["value"] == 1


def test_load_provider_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LTT_PROVIDER_ENDPOINT", "https://provider.local/ticks")
    monkeypatch.setenv("LTT_PROVIDER_NAME", "demo")
    monkeypatch.setenv("LTT_PROVIDER_SYMBOL", "EURUSD")
    monkeypatch.setenv("LTT_PROVIDER_API_KEY", "secret")
    monkeypatch.setenv("LTT_PROVIDER_API_KEY_HEADER", "X-API-Key")

    config = load_config()

    assert config.endpoints.provider_endpoint == "https://provider.local/ticks"
    assert config.provider.provider_name == "demo"
    assert config.provider.symbol == "EURUSD"
    assert config.provider.credentials["api_key"] == "secret"
    assert config.provider.credentials["api_key_header"] == "X-API-Key"
