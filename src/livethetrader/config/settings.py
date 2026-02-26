from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LimitsConfig:
    max_ticks_per_run: int = 54_000
    interface_history_limit: int = 20


@dataclass(slots=True)
class EndpointsConfig:
    dashboard_base_url: str = "http://127.0.0.1:8000"
    provider_endpoint: str = ""


@dataclass(slots=True)
class ProviderSettingsConfig:
    provider_name: str = ""
    symbol: str = ""
    credentials: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ThresholdsConfig:
    confidence_min: float = 0.55
    risk_rejection_max: float = 0.45


@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    service_name: str = "livethetrader"


@dataclass(slots=True)
class MLConfig:
    artifact_path: str = ""
    fallback_mode: str = "strict"


@dataclass(slots=True)
class AppConfig:
    symbols: list[str] = field(default_factory=lambda: ["EURUSD"])
    timeframes: list[str] = field(default_factory=lambda: ["1m", "5m", "15m"])
    poll_interval_seconds: float = 2.0
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    endpoints: EndpointsConfig = field(default_factory=EndpointsConfig)
    provider: ProviderSettingsConfig = field(default_factory=ProviderSettingsConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ml: MLConfig = field(default_factory=MLConfig)


ENV_CONFIG_PATH = "LTT_CONFIG_FILE"


def load_config(config_path: str | None = None) -> AppConfig:
    config = AppConfig()

    resolved_path = config_path or os.getenv(ENV_CONFIG_PATH)
    if resolved_path:
        _apply_file_overrides(config, Path(resolved_path))

    _apply_env_overrides(config)
    return config


def _apply_file_overrides(config: AppConfig, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Configuration file must contain a JSON object")

    _apply_mapping_overrides(config, payload)


def _apply_mapping_overrides(config: AppConfig, payload: dict[str, Any]) -> None:
    if "symbols" in payload:
        config.symbols = _as_list(payload["symbols"])
    if "timeframes" in payload:
        config.timeframes = _as_list(payload["timeframes"])
    if "poll_interval_seconds" in payload:
        config.poll_interval_seconds = float(payload["poll_interval_seconds"])

    limits = payload.get("limits")
    if isinstance(limits, dict):
        if "max_ticks_per_run" in limits:
            config.limits.max_ticks_per_run = int(limits["max_ticks_per_run"])
        if "interface_history_limit" in limits:
            config.limits.interface_history_limit = int(limits["interface_history_limit"])

    endpoints = payload.get("endpoints")
    if isinstance(endpoints, dict):
        if "dashboard_base_url" in endpoints:
            config.endpoints.dashboard_base_url = str(endpoints["dashboard_base_url"])
        if "provider_endpoint" in endpoints:
            config.endpoints.provider_endpoint = str(endpoints["provider_endpoint"])

    provider = payload.get("provider")
    if isinstance(provider, dict):
        if "provider_name" in provider:
            config.provider.provider_name = str(provider["provider_name"])
        if "symbol" in provider:
            config.provider.symbol = str(provider["symbol"])

        credentials = provider.get("credentials")
        if isinstance(credentials, dict):
            config.provider.credentials = {
                str(key): str(value)
                for key, value in credentials.items()
                if str(value).strip()
            }

    thresholds = payload.get("thresholds")
    if isinstance(thresholds, dict):
        if "confidence_min" in thresholds:
            config.thresholds.confidence_min = float(thresholds["confidence_min"])
        if "risk_rejection_max" in thresholds:
            config.thresholds.risk_rejection_max = float(thresholds["risk_rejection_max"])

    logging = payload.get("logging")
    if isinstance(logging, dict):
        if "level" in logging:
            config.logging.level = str(logging["level"]).upper()
        if "service_name" in logging:
            config.logging.service_name = str(logging["service_name"])

    ml = payload.get("ml")
    if isinstance(ml, dict):
        if "artifact_path" in ml:
            config.ml.artifact_path = str(ml["artifact_path"])
        if "fallback_mode" in ml:
            config.ml.fallback_mode = str(ml["fallback_mode"])


def _apply_env_overrides(config: AppConfig) -> None:
    if symbols := os.getenv("LTT_SYMBOLS"):
        config.symbols = _split_csv(symbols)
    if timeframes := os.getenv("LTT_TIMEFRAMES"):
        config.timeframes = _split_csv(timeframes)

    if poll_interval := os.getenv("LTT_POLL_INTERVAL_SECONDS"):
        config.poll_interval_seconds = float(poll_interval)

    if max_ticks := os.getenv("LTT_MAX_TICKS_PER_RUN"):
        config.limits.max_ticks_per_run = int(max_ticks)
    if history_limit := os.getenv("LTT_INTERFACE_HISTORY_LIMIT"):
        config.limits.interface_history_limit = int(history_limit)

    if base_url := os.getenv("LTT_DASHBOARD_BASE_URL"):
        config.endpoints.dashboard_base_url = base_url
    if provider_endpoint := os.getenv("LTT_PROVIDER_ENDPOINT"):
        config.endpoints.provider_endpoint = provider_endpoint

    if provider_name := os.getenv("LTT_PROVIDER_NAME"):
        config.provider.provider_name = provider_name
    if provider_symbol := os.getenv("LTT_PROVIDER_SYMBOL"):
        config.provider.symbol = provider_symbol

    provider_credentials = {
        "api_key": os.getenv("LTT_PROVIDER_API_KEY", ""),
        "api_key_header": os.getenv("LTT_PROVIDER_API_KEY_HEADER", ""),
        "api_key_prefix": os.getenv("LTT_PROVIDER_API_KEY_PREFIX", ""),
        "auth_payload": os.getenv("LTT_PROVIDER_AUTH_PAYLOAD", ""),
    }
    config.provider.credentials.update(
        {key: value for key, value in provider_credentials.items() if value.strip()}
    )

    if confidence_min := os.getenv("LTT_CONFIDENCE_MIN"):
        config.thresholds.confidence_min = float(confidence_min)
    if risk_rejection_max := os.getenv("LTT_RISK_REJECTION_MAX"):
        config.thresholds.risk_rejection_max = float(risk_rejection_max)

    if log_level := os.getenv("LTT_LOG_LEVEL"):
        config.logging.level = log_level.upper()
    if log_service := os.getenv("LTT_LOG_SERVICE_NAME"):
        config.logging.service_name = log_service

    if ml_artifact_path := os.getenv("LTT_ML_ARTIFACT_PATH"):
        config.ml.artifact_path = ml_artifact_path
    if ml_fallback_mode := os.getenv("LTT_ML_FALLBACK_MODE"):
        config.ml.fallback_mode = ml_fallback_mode


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return _split_csv(str(value))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
