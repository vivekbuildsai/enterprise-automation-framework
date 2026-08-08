from __future__ import annotations

from collections.abc import Callable
from typing import Any

from framework.testdata.providers.base_provider import DataProvider


class DatabaseDataProvider(DataProvider):
    """Adapts any repository lookup method (`SubscriberRepository.
    get_by_id`, `TenantRepository.find_by_code`, ...) to the `DataProvider`
    interface. Repositories don't share a common lookup method name/signature
    across domains (`framework/database/repositories`, by design — see
    docs/RepositoryPattern.md), so this wraps whichever callable the caller
    passes in rather than assuming one.
    """

    def __init__(self, fetch_fn: Callable[[str], Any]) -> None:
        self._fetch_fn = fetch_fn

    def fetch(self, key: str) -> Any:
        return self._fetch_fn(key)
