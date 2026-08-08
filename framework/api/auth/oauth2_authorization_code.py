from __future__ import annotations

import time
from collections.abc import Generator

import httpx

from framework.api.constants import Headers
from framework.api.exceptions import ApiAuthenticationError
from framework.logger import get_logger

_logger = get_logger("OAuth2AuthorizationCodeAuth")
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


class OAuth2AuthorizationCodeAuth(httpx.Auth):
    """OAuth2 "authorization code" grant (RFC 6749 §4.1) — user-delegated
    auth. The interactive consent step (redirecting a real user to an IdP
    login page) is out of scope for an API client and belongs to whatever
    obtained `authorization_code` (a UI test driving the consent screen, a
    fixture backed by a test IdP, etc.) — this strategy owns the token
    exchange and refresh from that point on, which is the part that's
    actually testable and reusable across services.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_code: str,
        *,
        timeout_seconds: float = 30,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._authorization_code = authorization_code
        self._timeout_seconds = timeout_seconds
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at_monotonic: float = 0.0

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        if self._access_token is None:
            self._exchange_code_for_token()
        elif time.monotonic() >= self._expires_at_monotonic:
            self._refresh_access_token()

        request.headers[Headers.AUTHORIZATION] = f"Bearer {self._access_token}"
        yield request

    def _exchange_code_for_token(self) -> None:
        payload = {
            "grant_type": "authorization_code",
            "code": self._authorization_code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        _logger.info(f"Exchanging authorization code for a token at {self._token_url}")
        self._request_token(payload)

    def _refresh_access_token(self) -> None:
        if not self._refresh_token:
            return  # no refresh token issued; keep using the (possibly stale) access token
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        _logger.info("Refreshing OAuth2 access token")
        self._request_token(payload)

    def _request_token(self, payload: dict[str, str]) -> None:
        try:
            response = httpx.post(self._token_url, data=payload, timeout=self._timeout_seconds)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise ApiAuthenticationError(
                f"OAuth2 authorization-code token request failed at {self._token_url}: {exc}"
            ) from exc

        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token", self._refresh_token)
        expires_in = int(body.get("expires_in", 3600))
        self._expires_at_monotonic = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS
