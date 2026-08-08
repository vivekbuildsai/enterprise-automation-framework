from __future__ import annotations

from collections.abc import Generator

import httpx

from framework.api.constants import Headers


class BearerTokenAuth(httpx.Auth):
    """Static bearer token — the caller (typically a service after a login
    call) already has the token and just wants it attached to every request.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers[Headers.AUTHORIZATION] = f"Bearer {self._token}"
        yield request
