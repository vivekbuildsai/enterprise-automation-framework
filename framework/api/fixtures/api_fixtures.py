from __future__ import annotations

from collections.abc import Generator

import pytest

from framework.api.auth import AuthFactory
from framework.api.client import ApiClient
from framework.api.services import ApiValidator, AuthService, UserService
from framework.config import EnvironmentSettings
from framework.exceptions import ConfigurationError

_DEFAULT_SERVICE_KEY = "dummyjson"


@pytest.fixture
def api_service_key() -> str:
    """Which entry in `settings.api` a test targets. Override at the test or
    module level (`@pytest.fixture def api_service_key(): return "subscriber_management"`)
    to point every fixture in this file at a different service without
    touching test bodies — the same "config drives it, not code" principle
    as `ValidationMode`.
    """
    return _DEFAULT_SERVICE_KEY


@pytest.fixture
def api_client(
    settings: EnvironmentSettings, api_service_key: str
) -> Generator[ApiClient, None, None]:
    """Function-scoped `ApiClient` for `api_service_key`, one per test — like
    the UI layer's `page` fixture, this avoids state leaking between tests
    (e.g. a session cookie from one test's login silently authenticating
    the next test).
    """
    if api_service_key not in settings.api:
        env_name = settings.environment.value
        raise ConfigurationError(
            f"No API config for '{api_service_key}' in the '{env_name}' environment — "
            f"add it under `api:` in config/environments/{env_name}.yaml"
        )

    config = settings.api[api_service_key]
    auth = AuthFactory.from_config(config)
    client = ApiClient(str(config.base_url), auth=auth, timeout_seconds=config.timeout_seconds)

    yield client

    client.close()


@pytest.fixture
def auth_service(api_client: ApiClient) -> AuthService:
    return AuthService(api_client)


@pytest.fixture
def user_service(api_client: ApiClient) -> UserService:
    return UserService(api_client)


@pytest.fixture
def api_validator(api_client: ApiClient) -> ApiValidator:
    return ApiValidator(api_client)
