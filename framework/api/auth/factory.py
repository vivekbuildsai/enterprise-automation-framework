from __future__ import annotations

import httpx

from framework.api.auth.api_key_auth import ApiKeyAuth
from framework.api.auth.base import NoAuth
from framework.api.auth.basic_auth import BasicAuthStrategy
from framework.api.auth.oauth2_client_credentials import OAuth2ClientCredentialsAuth
from framework.config.models import ApiEndpointConfig
from framework.exceptions import ConfigurationError


class AuthFactory:
    """Factory Pattern (mirrors `BrowserFactory`): builds the right
    `httpx.Auth` strategy from an `ApiEndpointConfig.auth_type`, for the
    strategies that are fully determined by static config.

    `bearer`, `jwt`, and `oauth2_authorization_code` are deliberately *not*
    buildable here — they need a token obtained at runtime (a login call, a
    user-consent redirect), so callers construct
    `BearerTokenAuth`/`JwtAuth`/`OAuth2AuthorizationCodeAuth` directly once
    they have that token/code. `from_config` covers the strategies a service
    can wire up purely from environment settings.
    """

    _STATIC_AUTH_TYPES = frozenset({"none", "basic", "oauth2", "api_key"})

    @staticmethod
    def from_config(config: ApiEndpointConfig) -> httpx.Auth:
        match config.auth_type:
            case "none":
                return NoAuth()
            case "basic":
                return BasicAuthStrategy(config.client_id, config.client_secret)
            case "api_key":
                return ApiKeyAuth(config.api_key)
            case "oauth2":
                if not config.token_url:
                    raise ConfigurationError(
                        "auth_type 'oauth2' requires 'token_url' to be set "
                        "in the environment config"
                    )
                return OAuth2ClientCredentialsAuth(
                    token_url=config.token_url,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    timeout_seconds=config.timeout_seconds,
                )
            case "bearer" | "jwt" | "oauth2_authorization_code":
                raise ConfigurationError(
                    f"auth_type '{config.auth_type}' needs a runtime-obtained token — "
                    "construct the matching auth strategy directly instead of via "
                    "AuthFactory.from_config"
                )
            case "mtls":
                raise ConfigurationError(
                    "auth_type 'mtls' is a transport-level concern (client certificates) — "
                    "configure it on the httpx.Client/ApiClient directly, not via an Auth strategy"
                )
            case _:
                raise ConfigurationError(f"Unknown auth_type: '{config.auth_type}'")
