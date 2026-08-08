"""Shared error handling for this framework's CLI entry points
(`framework.cli`, `framework.discovery.__main__`, `framework.sync.__main__`)
— each remains an independently runnable `main()` (`python -m
framework.discovery ...` works without going through `python -m
framework`), so this is one small, dependency-free helper all three
import rather than three near-identical `try/except` blocks.
"""

from __future__ import annotations

import json
import sys
import zipfile
from collections.abc import Callable
from typing import Any

from framework.exceptions import ConfigurationError

_EXPECTED_ERRORS = (
    FileNotFoundError,
    ValueError,
    ConfigurationError,
    json.JSONDecodeError,
    zipfile.BadZipFile,
)


def run_command(func: Callable[[Any], int | None], args: Any) -> int:
    """Runs one argparse subcommand handler. Turns expected, actionable
    failure modes (a missing file, an invalid `--env` name, a corrupt
    archive, a `ConfigurationError` raised deliberately by the framework)
    into a clean one-line stderr message + exit code 1, instead of a raw
    traceback. `func` may return `None` (success) or an explicit exit
    code; anything else propagates — hiding a genuine bug behind a
    generic message would make it harder to diagnose, not easier.
    """
    try:
        result = func(args)
    except _EXPECTED_ERRORS as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return result if isinstance(result, int) else 0
