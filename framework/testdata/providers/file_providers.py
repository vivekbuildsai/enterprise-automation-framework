from __future__ import annotations

from typing import Any

from framework.testdata.providers.base_provider import DataProvider
from framework.utilities.test_data_loader import TestDataLoader


class JsonProvider(DataProvider):
    """`key` is a path relative to `data/testdata/` — delegates to the
    existing `TestDataLoader` rather than re-implementing file resolution.
    """

    def fetch(self, key: str) -> Any:
        return TestDataLoader.load_json(key)


class CsvProvider(DataProvider):
    def fetch(self, key: str) -> Any:
        return TestDataLoader.load_csv(key)


class ExcelProvider(DataProvider):
    def __init__(self, *, sheet_name: str | None = None) -> None:
        self._sheet_name = sheet_name

    def fetch(self, key: str) -> Any:
        return TestDataLoader.load_excel(key, sheet_name=self._sheet_name)
