from __future__ import annotations

from livethetrader.config import load_config
from livethetrader.logging import configure_logging


def pytest_sessionstart(session) -> None:  # noqa: ANN001
    config = load_config()
    configure_logging(level=config.logging.level, service_name=config.logging.service_name)
