# Dataset Management

How `framework/testdata/datasets/`, `providers/`, `importers/`,
`exporters/`, and `cache/` fit together — the file/external-data side of
the TDM layer, as opposed to `builders/`/`factories`/`scenarios` (the
code-composed side).

## `DatasetLoader` — the single entry point for `data/testdata/` files

Wraps `framework.utilities.TestDataLoader` (JSON/CSV/Excel — reused, not
duplicated) and adds:

```python
DatasetLoader.load_json(...)          # delegates to TestDataLoader
DatasetLoader.load_csv(...)           # delegates to TestDataLoader
DatasetLoader.load_excel(...)         # delegates to TestDataLoader
DatasetLoader.load_for_environment(...)  # delegates to TestDataLoader

DatasetLoader.load_yaml("path.yaml")                          # new
DatasetLoader.load_versioned("module", "v1", Environment.DEV)  # data/testdata/<module>/<version>/<env>.json
DatasetLoader.load_shared("tenants")                            # data/testdata/shared/<name>.json
DatasetLoader.load_scenario("roaming_subscriber")                # data/testdata/scenarios/<name>.json
```

- **Versioned datasets**: bump `version` (`"v1"` -> `"v2"`) when a
  dataset's shape changes incompatibly, so tests pinned to `"v1"` keep
  passing against the old shape while others move to `"v2"`.
- **Shared datasets**: `data/testdata/shared/` for data meant to be reused
  across modules, rather than owned by one module's subdirectory.
- **File-authored scenarios**: `data/testdata/scenarios/` for scenario data
  easier to author as a JSON file than as `ScenarioLibrary` builder chains
  (e.g. handed off by QA) — distinct from the code-composed
  `framework.testdata.scenarios.ScenarioLibrary` (see
  [ScenarioLibrary.md](ScenarioLibrary.md)).

## `DatasetRegistry` — named lookup with caching

```python
from framework.testdata.datasets import DatasetRegistry, datasets  # `datasets` is a shared instance

datasets.register("roaming_tenants", lambda: DatasetLoader.load_shared("tenants"))
tenants = datasets.get("roaming_tenants")   # loads once
tenants = datasets.get("roaming_tenants")   # cached, no re-read
```

Register once (e.g. in a `conftest.py`), reference by name everywhere else
— a test never needs to know or repeat the underlying file path.

## Data Providers — one interface, five sources

`framework/testdata/providers/DataProvider` is a one-method contract
(`fetch(key) -> Any`) implemented by:

| Provider | Wraps |
|---|---|
| `DatabaseDataProvider` | any repository lookup method (`SubscriberRepository.get_by_id`, ...) |
| `ApiDataProvider` | `ApiClient.get()` against a `{key}`-templated endpoint |
| `JsonProvider` / `CsvProvider` / `ExcelProvider` | `TestDataLoader` (same conventions as `DatasetLoader`) |
| `EnvironmentVariableProvider` | `os.environ`, with `required`/`default` |

Code that needs "some test data, from whichever source a test configures"
can accept a `DataProvider` and call `.fetch(key)` without caring which
concrete provider it got — e.g. a validator comparing "expected" data could
source that expectation from a database row in one environment and a JSON
fixture in another, without changing.

## Importers / Exporters — arbitrary file paths

`DatasetLoader`/providers work within the `data/testdata/` convention.
`framework/testdata/importers/` (`CsvImporter`, `JsonImporter`,
`ExcelImporter`) and `exporters/` (mirror set) work with **any** file path
— for a file a QA engineer hands off ad hoc, or exporting generated data as
a CI artifact:

```python
records = [dataclasses.asdict(s) for s in SubscriberBuilder().build_many(100)]
CsvExporter.export(records, "artifacts/load_test_subscribers.csv")
```

## Cache

`framework/testdata/cache/DataCache` — in-memory, optional TTL, used
internally by `DatasetRegistry` (and available directly) so re-reading the
same dataset within a test session doesn't re-hit disk/DB/API every time.
Uses a sentinel internally to distinguish "not cached" from "cached value
is `None`" — a legitimately `None` lookup result caches correctly instead
of being treated as a permanent miss.

## Testing

`tests/testdata/unit/test_datasets.py`, `test_providers.py`,
`test_importers_exporters.py`, `test_cache.py` — 33 tests total, covering
every format (JSON/YAML/CSV/Excel), the versioned/shared/scenario file
conventions, provider error handling, and cache TTL expiry.
