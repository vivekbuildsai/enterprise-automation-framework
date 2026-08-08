from __future__ import annotations

from typing import Any

import yaml

from framework.enums import Environment
from framework.exceptions import TestDataError
from framework.project_root import PROJECT_ROOT
from framework.utilities.test_data_loader import TestDataLoader

_TESTDATA_DIR = PROJECT_ROOT / "data" / "testdata"
_SHARED_DIR = "shared"
_SCENARIOS_DIR = "scenarios"


class DatasetLoader:
    """The testdata layer's single entry point for loading data off disk —
    wraps `framework.utilities.TestDataLoader` (JSON/CSV/Excel; reused, not
    duplicated) and adds YAML support, versioned datasets, and the shared/
    scenario dataset directory conventions.
    """

    # -- Delegates to TestDataLoader (kept here so callers only need one
    # import for every on-disk format) -----------------------------------
    load_json = staticmethod(TestDataLoader.load_json)
    load_csv = staticmethod(TestDataLoader.load_csv)
    load_excel = staticmethod(TestDataLoader.load_excel)
    load_for_environment = staticmethod(TestDataLoader.load_for_environment)

    @staticmethod
    def load_yaml(relative_path: str) -> Any:
        path = _TESTDATA_DIR / relative_path
        if not path.exists():
            raise TestDataError(f"No test data file at '{path}' (looked under {_TESTDATA_DIR})")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @staticmethod
    def load_versioned(module: str, version: str, environment: Environment) -> Any:
        """`data/testdata/<module>/<version>/<environment>.json` — the
        versioned-dataset convention: bump `version` (e.g. "v1" -> "v2")
        when a dataset's shape changes incompatibly, so tests pinned to
        "v1" keep passing against the old shape while others move to "v2".
        """
        return DatasetLoader.load_json(f"{module}/{version}/{environment.value}.json")

    @staticmethod
    def load_shared(name: str) -> Any:
        """`data/testdata/shared/<name>.json` — datasets meant to be reused
        across modules (e.g. a common list of test tenants) rather than
        owned by one module's own subdirectory.
        """
        return DatasetLoader.load_json(f"{_SHARED_DIR}/{name}.json")

    @staticmethod
    def load_scenario(name: str) -> Any:
        """`data/testdata/scenarios/<name>.json` — file-authored scenario
        data (e.g. handed off by QA as a spreadsheet-turned-JSON), distinct
        from the code-composed `framework.testdata.scenarios.ScenarioLibrary`
        — use this for scenario data that's easier to author as a data file
        than as builder chains.
        """
        return DatasetLoader.load_json(f"{_SCENARIOS_DIR}/{name}.json")
