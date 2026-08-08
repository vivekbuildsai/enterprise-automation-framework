from __future__ import annotations

from typing import Any

from framework.api.client import ApiClient


class ApiSeeder:
    """Seeds test data via API POST calls — for records the API layer
    owns rather than a direct DB write. Reuses `ApiClient` (retry/logging/
    Allure middleware included) instead of talking to `httpx` directly.
    Returns each created record's response body, so a cleanup service can
    later target it for deletion by whatever ID field the response
    includes.
    """

    def __init__(self, api_client: ApiClient, endpoint: str) -> None:
        self._client = api_client
        self._endpoint = endpoint

    def seed_one(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(self._endpoint, json=payload)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def seed_many(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.seed_one(payload) for payload in payloads]
