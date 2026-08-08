from __future__ import annotations

from collections.abc import Callable
from typing import Any

from framework.exceptions import TestDataError


class DatasetRegistry:
    """Named dataset lookup: register once (`register("roaming_subscribers",
    loader)`), then every test references it by name (`registry.get(
    "roaming_subscribers")`) instead of duplicating a file path or loader
    call at every use site. `loader` is any zero-arg callable — typically a
    `DatasetLoader.load_*` partial — so registration doesn't care whether
    the dataset is JSON, YAML, CSV, or Excel.

    Results are cached after first resolution (datasets are read-only test
    fixtures, not something a test mutates and expects re-read) — call
    `invalidate()`/`clear()` if a test genuinely needs a fresh read.
    """

    def __init__(self) -> None:
        self._loaders: dict[str, Callable[[], Any]] = {}
        self._cache: dict[str, Any] = {}

    def register(self, name: str, loader: Callable[[], Any]) -> None:
        self._loaders[name] = loader
        self._cache.pop(name, None)

    def is_registered(self, name: str) -> bool:
        return name in self._loaders

    def get(self, name: str) -> Any:
        if name not in self._loaders:
            raise TestDataError(
                f"No dataset registered as '{name}'. Registered: {sorted(self._loaders)}"
            )
        if name not in self._cache:
            self._cache[name] = self._loaders[name]()
        return self._cache[name]

    def invalidate(self, name: str) -> None:
        self._cache.pop(name, None)

    def clear(self) -> None:
        self._loaders.clear()
        self._cache.clear()


datasets = DatasetRegistry()
