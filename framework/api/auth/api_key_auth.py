from __future__ import annotations

from collections.abc import Generator
from typing import Literal

import httpx

from framework.api.constants import Headers


class ApiKeyAuth(httpx.Auth):
    """API key auth, injected either as a header (default, e.g. `X-Api-Key`)
    or as a query parameter — some providers require the latter.
    """

    def __init__(
        self,
        api_key: str,
        *,
        key_name: str = Headers.API_KEY,
        location: Literal["header", "query"] = "header",
    ) -> None:
        self._api_key = api_key
        self._key_name = key_name
        self._location = location

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        if self._location == "header":
            request.headers[self._key_name] = self._api_key
        else:
            url = request.url.copy_merge_params({self._key_name: self._api_key})
            request.url = url
        yield request
