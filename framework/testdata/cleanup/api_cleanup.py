from __future__ import annotations

from framework.api.client import ApiClient
from framework.logger import get_logger

_logger = get_logger("ApiCleanupService")


class ApiCleanupService:
    """Deletes API-created test resources via DELETE calls — reuses
    `ApiClient` for the same retry/logging/Allure attachment every other
    API call in this framework gets. `endpoint_template` is a
    `str.format`-style path with an `{id}` placeholder, e.g. `"/users/{id}"`.
    """

    def __init__(self, api_client: ApiClient, endpoint_template: str) -> None:
        self._client = api_client
        self._endpoint_template = endpoint_template

    def delete(self, resource_id: str | int) -> None:
        endpoint = self._endpoint_template.format(id=resource_id)
        response = self._client.delete(endpoint)
        if response.status_code >= 400:
            _logger.warning(f"Cleanup DELETE {endpoint} returned {response.status_code}")

    def delete_many(self, resource_ids: list[str | int]) -> None:
        for resource_id in resource_ids:
            self.delete(resource_id)
