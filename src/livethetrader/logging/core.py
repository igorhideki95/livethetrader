from __future__ import annotations

import logging
from typing import Any

from livethetrader.logging.json_formatter import JsonLogFormatter

_DEFAULT_HANDLER_NAME = "livethetrader_json_handler"


_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(*, level: str = "INFO", service_name: str = "livethetrader") -> None:
    root = logging.getLogger()
    root.setLevel(_LEVELS.get(level.upper(), logging.INFO))

    for handler in root.handlers:
        if getattr(handler, "name", "") == _DEFAULT_HANDLER_NAME:
            handler.setFormatter(JsonLogFormatter(service_name=service_name))
            handler.setLevel(root.level)
            return

    handler = logging.StreamHandler()
    handler.name = _DEFAULT_HANDLER_NAME
    handler.setFormatter(JsonLogFormatter(service_name=service_name))
    handler.setLevel(root.level)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger.log(level, event, extra={"event_data": fields})
