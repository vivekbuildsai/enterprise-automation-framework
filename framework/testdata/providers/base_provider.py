from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DataProvider(ABC):
    """Common contract for every test-data source (database, REST API,
    JSON/CSV/Excel file, environment variable, ...): one `fetch(key)`
    method, so consuming code (fixtures, dataset resolution, validators)
    can accept "a provider" without caring which kind of source it is.
    """

    @abstractmethod
    def fetch(self, key: str) -> Any:
        raise NotImplementedError
