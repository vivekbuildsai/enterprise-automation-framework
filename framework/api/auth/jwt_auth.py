from __future__ import annotations

from collections.abc import Callable, Generator

import httpx

from framework.api.constants import Headers
from framework.logger import get_logger

_logger = get_logger("JwtAuth")


class JwtAuth(httpx.Auth):
    """Bearer-style JWT auth that transparently refreshes on a 401.

    `refresh_token` is called at most once per request (never loops forever
    on a still-failing refresh) and should return a fresh access token —
    typically by re-invoking a login/refresh-token API call.
    """

    def __init__(self, access_token: str, refresh_token: Callable[[], str] | None = None) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers[Headers.AUTHORIZATION] = f"Bearer {self._access_token}"
        response = yield request

        if response.status_code == 401 and self._refresh_token is not None:
            _logger.info("Access token rejected (401); refreshing and retrying once")
            self._access_token = self._refresh_token()
            request.headers[Headers.AUTHORIZATION] = f"Bearer {self._access_token}"
            yield request
