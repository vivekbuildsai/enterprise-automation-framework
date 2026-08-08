from __future__ import annotations

import time
from collections.abc import Generator

import httpx

from framework.api.constants import Headers
from framework.api.exceptions import ApiAuthenticationError
from framework.logger import get_logger

_logger = get_logger("OAuth2ClientCredentialsAuth")
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


class OAuth2ClientCredentialsAuth(httpx.Auth):
    """OAuth2 "client credentials" grant (RFC 6749 §4.4) — machine-to-machine
    auth with no user in the loop. Fetches a token lazily on first use and
    transparently re-fetches once it's within `_EXPIRY_SAFETY_MARGIN_SECONDS`
    of expiring, so callers never see a 401 from an expired token.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        scope: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._timeout_seconds = timeout_seconds
        self._access_token: str | None = None
        self._expires_at_monotonic: float = 0.0

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        if self._token_is_expired():
            self._fetch_token()
        request.headers[Headers.AUTHORIZATION] = f"Bearer {self._access_token}"
        yield request

    def _token_is_expired(self) -> bool:
        return self._access_token is None or time.monotonic() >= self._expires_at_monotonic

    def _fetch_token(self) -> None:
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scope:
            payload["scope"] = self._scope

        _logger.info(f"Requesting OAuth2 client-credentials token from {self._token_url}")
        try:
            response = httpx.post(self._token_url, data=payload, timeout=self._timeout_seconds)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise ApiAuthenticationError(
                f"Failed to obtain OAuth2 client-credentials token from {self._token_url}: {exc}"
            ) from exc

        self._access_token = body["access_token"]
        expires_in = int(body.get("expires_in", 3600))
        self._expires_at_monotonic = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS
