"""Pluggable authentication for the API client.

`httpx.Auth` is the extension point every strategy below implements:
`auth_flow(request)` is a generator that yields the (possibly modified)
request and receives the response back, so a strategy can inspect a 401 and
retry with refreshed credentials — that's what makes token refresh (JWT,
OAuth2) possible without the client knowing anything about auth internals.

Passing any of these to `ApiClient(auth=...)` (or per-request) is the whole
integration surface — the client never branches on "which kind of auth".
"""

from __future__ import annotations

from collections.abc import Generator

import httpx

AuthStrategy = httpx.Auth
"""Type alias documenting the extension point. Any `httpx.Auth` subclass
(the strategies in this package, or a team-authored one) can be passed
wherever an `AuthStrategy` is expected."""


class NoAuth(httpx.Auth):
    """No-op strategy for `auth_type: none` — makes "no authentication" an
    explicit, pluggable choice rather than a special-cased `None` check
    scattered through client code.
    """

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        yield request
