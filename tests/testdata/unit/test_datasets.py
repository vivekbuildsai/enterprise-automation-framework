from __future__ import annotations

import pytest

from framework.enums import Environment
from framework.exceptions import TestDataError
from framework.testdata.datasets import DatasetLoader, DatasetRegistry

pytestmark = pytest.mark.testdata


def test_load_yaml() -> None:
    data = DatasetLoader.load_yaml("testdata_demo/sample.yaml")
    assert data["note"]
    assert len(data["tenants"]) == 2


def test_load_shared() -> None:
    data = DatasetLoader.load_shared("tenants")
    assert len(data["tenants"]) == 2


def test_load_scenario() -> None:
    data = DatasetLoader.load_scenario("roaming_subscriber")
    assert data["scenario"] == "roaming_subscriber"


def test_load_versioned() -> None:
    data = DatasetLoader.load_versioned("testdata_demo", "v1", Environment.DEV)
    assert data["version"] == "v1"


def test_load_json_delegates_to_test_data_loader() -> None:
    data = DatasetLoader.load_json("subscriber_management/dev.json")
    assert "search_terms" in data


def test_missing_dataset_raises_test_data_error() -> None:
    with pytest.raises(TestDataError):
        DatasetLoader.load_json("does/not/exist.json")


def test_dataset_registry_registers_and_resolves() -> None:
    registry = DatasetRegistry()
    registry.register("roaming", lambda: DatasetLoader.load_scenario("roaming_subscriber"))
    assert registry.is_registered("roaming")
    assert registry.get("roaming")["scenario"] == "roaming_subscriber"


def test_dataset_registry_caches_result() -> None:
    calls = []

    def loader() -> dict[str, int]:
        calls.append(1)
        return {"value": 1}

    registry = DatasetRegistry()
    registry.register("counted", loader)
    registry.get("counted")
    registry.get("counted")
    assert len(calls) == 1


def test_dataset_registry_invalidate_forces_reload() -> None:
    calls = []

    def loader() -> dict[str, int]:
        calls.append(1)
        return {"value": len(calls)}

    registry = DatasetRegistry()
    registry.register("counted", loader)
    registry.get("counted")
    registry.invalidate("counted")
    registry.get("counted")
    assert len(calls) == 2


def test_dataset_registry_raises_for_unregistered_name() -> None:
    registry = DatasetRegistry()
    with pytest.raises(TestDataError):
        registry.get("missing")
