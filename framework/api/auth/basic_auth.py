from __future__ import annotations

from collections.abc import Generator

import httpx


class BasicAuthStrategy(httpx.Auth):
    """RFC 7617 HTTP Basic auth. Thin wrapper around `httpx.BasicAuth` so
    every auth strategy in this framework is imported from
    `framework.api.auth` with a consistent naming convention, rather than
    mixing httpx's own classes with ours at call sites.
    """

    def __init__(self, username: str, password: str) -> None:
        self._delegate = httpx.BasicAuth(username, password)

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        yield from self._delegate.auth_flow(request)
