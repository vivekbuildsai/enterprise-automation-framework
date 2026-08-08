from __future__ import annotations

import pytest

from framework.exceptions import TestDataError
from framework.testdata.providers import (
    CsvProvider,
    DatabaseDataProvider,
    EnvironmentVariableProvider,
    ExcelProvider,
    JsonProvider,
)

pytestmark = pytest.mark.testdata


def test_database_data_provider_wraps_any_callable() -> None:
    lookup = {"S1": "subscriber-one"}
    provider = DatabaseDataProvider(lookup.get)
    assert provider.fetch("S1") == "subscriber-one"
    assert provider.fetch("missing") is None


def test_environment_variable_provider_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TDM_TEST_VAR", "hello")
    provider = EnvironmentVariableProvider()
    assert provider.fetch("TDM_TEST_VAR") == "hello"


def test_environment_variable_provider_returns_default_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TDM_MISSING_VAR", raising=False)
    provider = EnvironmentVariableProvider(default="fallback")
    assert provider.fetch("TDM_MISSING_VAR") == "fallback"


def test_environment_variable_provider_required_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TDM_REQUIRED_MISSING", raising=False)
    provider = EnvironmentVariableProvider(required=True)
    with pytest.raises(TestDataError):
        provider.fetch("TDM_REQUIRED_MISSING")


def test_json_provider_loads_existing_module_data() -> None:
    data = JsonProvider().fetch("subscriber_management/dev.json")
    assert "search_terms" in data


def test_csv_provider_loads_existing_module_data() -> None:
    rows = CsvProvider().fetch("subscriber_management/subscribers.csv")
    assert isinstance(rows, list)
    assert rows


def test_excel_provider_loads_existing_module_data() -> None:
    rows = ExcelProvider().fetch("subscriber_management/subscribers.xlsx")
    assert isinstance(rows, list)
    assert rows
