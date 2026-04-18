from __future__ import annotations

import json
import logging
from typing import Any


LOGGER_NAMESPACE = "invoice_assistant"


def get_app_logger(name: str = "app") -> logging.Logger:
    logger_name = LOGGER_NAMESPACE if name == "app" else f"{LOGGER_NAMESPACE}.{name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    return logger


def log_event(logger: logging.Logger, event: str, **payload: Any) -> None:
    logger.info(
        "%s %s",
        event,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
    )
