from __future__ import annotations

from collections.abc import Generator

import httpx


class CookieAuth(httpx.Auth):
    """Session-cookie auth — attaches a pre-obtained session cookie to every
    request. Useful for backends that authenticate via a session cookie set
    at login rather than a bearer token.
    """

    def __init__(self, cookie_name: str, cookie_value: str) -> None:
        self._cookie_name = cookie_name
        self._cookie_value = cookie_value

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Cookie"] = f"{self._cookie_name}={self._cookie_value}"
        yield request
