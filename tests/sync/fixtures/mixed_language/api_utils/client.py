import requests


class ApiTestUtils:
    """Small Python helper used by the automation team to seed/verify
    backend state before/after the TypeScript UI suite runs — a real,
    common "mostly-one-language, one-supporting-language" repository
    shape, not an evenly-split one.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def get_user(self, user_id: int) -> dict:
        response = requests.get(f"{self._base_url}/users/{user_id}")
        response.raise_for_status()
        return response.json()
