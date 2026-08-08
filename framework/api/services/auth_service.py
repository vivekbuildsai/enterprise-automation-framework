from __future__ import annotations

import httpx

from framework.api.client import ApiClient
from framework.api.endpoints import Endpoints
from framework.api.models import LoginRequest, LoginResponse, User


class AuthService:
    """Domain facade over `ApiClient` for authentication — the layer tests
    and (eventually) UI hybrid-validation code call, instead of building
    requests by hand. Keeps `self.last_response` so a caller that wants to
    run `ResponseValidator` against status/headers/timing (not just the
    parsed model) doesn't have to duplicate the call.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self.last_response: httpx.Response | None = None

    def login(self, username: str, password: str) -> LoginResponse:
        request = LoginRequest(username=username, password=password)
        self.last_response = self._client.post(Endpoints.LOGIN, json=request.model_dump())
        return LoginResponse.model_validate(self.last_response.json())

    def get_current_user(self, access_token: str) -> User:
        self.last_response = self._client.get(
            Endpoints.AUTH_ME, headers={"Authorization": f"Bearer {access_token}"}
        )
        return User.model_validate(self.last_response.json())
