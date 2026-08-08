from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger as _loguru_logger

if TYPE_CHECKING:
    from loguru import Logger

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_state = {"configured": False}

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[component]}</cyan> | "
    "<level>{message}</level>"
)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[component]} | "
    "{name}:{function}:{line} | {message}"
)


def configure_logging(*, log_file_name: str = "execution.log", level: str = "INFO") -> None:
    """Wire up console + rotating file sinks. Idempotent — safe to call from
    multiple conftest.py fixtures without duplicating sinks.
    """
    if _state["configured"]:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _loguru_logger.remove()
    _loguru_logger.configure(extra={"component": "framework"})

    _loguru_logger.add(
        sys.stdout,
        format=_CONSOLE_FORMAT,
        level=level,
        colorize=True,
        backtrace=False,
        diagnose=False,
    )
    _loguru_logger.add(
        _LOG_DIR / log_file_name,
        format=_FILE_FORMAT,
        level="DEBUG",
        rotation="50 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    _state["configured"] = True


def get_logger(component: str) -> Logger:
    """Return a logger bound to a named component (e.g. page name, service
    name) so log lines are attributable at a glance:
    `2026-07-29 ... | INFO | LoginPage | Filled username field`.
    """
    configure_logging()
    return _loguru_logger.bind(component=component)
