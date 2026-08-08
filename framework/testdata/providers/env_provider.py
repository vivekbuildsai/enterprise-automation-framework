from __future__ import annotations

import os

from framework.exceptions import TestDataError
from framework.testdata.providers.base_provider import DataProvider


class EnvironmentVariableProvider(DataProvider):
    """Fetches test data (typically secrets/config that must never be
    hardcoded — credentials, API keys) from process environment variables.
    """

    def __init__(self, *, required: bool = False, default: str | None = None) -> None:
        self._required = required
        self._default = default

    def fetch(self, key: str) -> str | None:
        value = os.environ.get(key, self._default)
        if value is None and self._required:
            raise TestDataError(f"Required environment variable '{key}' is not set")
        return value
