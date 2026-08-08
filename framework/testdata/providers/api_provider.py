from __future__ import annotations

from typing import Any

from framework.api.client import ApiClient
from framework.testdata.providers.base_provider import DataProvider


class ApiDataProvider(DataProvider):
    """Fetches test data from a REST endpoint via the existing `ApiClient`
    (reused, not reimplemented — inherits its retry/logging/Allure
    middleware for free). `endpoint_template` is a `str.format`-style path
    with a `{key}` placeholder, e.g. `"/users/{key}"`.
    """

    def __init__(self, api_client: ApiClient, endpoint_template: str) -> None:
        self._client = api_client
        self._endpoint_template = endpoint_template

    def fetch(self, key: str) -> Any:
        response = self._client.get(self._endpoint_template.format(key=key))
        return response.json()
