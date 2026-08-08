import httpx
import pytest

from framework.api.auth import (
    ApiKeyAuth,
    AuthFactory,
    BasicAuthStrategy,
    BearerTokenAuth,
    CookieAuth,
    JwtAuth,
    NoAuth,
    OAuth2ClientCredentialsAuth,
)
from framework.api.exceptions import ApiAuthenticationError
from framework.config.models import ApiEndpointConfig
from framework.exceptions import ConfigurationError


def _client_for(auth: httpx.Auth, handler) -> httpx.Client:
    return httpx.Client(base_url="http://test", auth=auth, transport=httpx.MockTransport(handler))


@pytest.mark.api
@pytest.mark.regression
class TestAuthStrategies:
    def test_no_auth_sends_no_authorization_header(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "Authorization" not in request.headers
            return httpx.Response(200)

        with _client_for(NoAuth(), handler) as client:
            client.get("/x")

    def test_bearer_token_auth_sets_header(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer abc123"
            return httpx.Response(200)

        with _client_for(BearerTokenAuth("abc123"), handler) as client:
            client.get("/x")

    def test_basic_auth_sets_header(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"].startswith("Basic ")
            return httpx.Response(200)

        with _client_for(BasicAuthStrategy("user", "pass"), handler) as client:
            client.get("/x")

    def test_api_key_auth_header_location(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["X-Api-Key"] == "secret-key"
            return httpx.Response(200)

        with _client_for(ApiKeyAuth("secret-key"), handler) as client:
            client.get("/x")

    def test_api_key_auth_query_location(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["api_key"] == "secret-key"
            return httpx.Response(200)

        auth = ApiKeyAuth("secret-key", key_name="api_key", location="query")
        with _client_for(auth, handler) as client:
            client.get("/x")

    def test_cookie_auth_sets_cookie_header(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Cookie"] == "session=xyz"
            return httpx.Response(200)

        with _client_for(CookieAuth("session", "xyz"), handler) as client:
            client.get("/x")


@pytest.mark.api
@pytest.mark.regression
class TestJwtAuthRefresh:
    def test_valid_token_is_used_without_refresh(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.headers["Authorization"])
            return httpx.Response(200)

        with _client_for(JwtAuth("good-token"), handler) as client:
            client.get("/x")

        assert calls == ["Bearer good-token"]

    def test_401_triggers_one_refresh_and_retry(self) -> None:
        responses = iter([httpx.Response(401), httpx.Response(200)])
        seen_tokens = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_tokens.append(request.headers["Authorization"])
            return next(responses)

        auth = JwtAuth("expired-token", refresh_token=lambda: "refreshed-token")
        with _client_for(auth, handler) as client:
            response = client.get("/x")

        assert response.status_code == 200
        assert seen_tokens == ["Bearer expired-token", "Bearer refreshed-token"]

    def test_401_without_refresh_callback_does_not_retry(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(401)

        with _client_for(JwtAuth("expired-token"), handler) as client:
            response = client.get("/x")

        assert response.status_code == 401
        assert len(calls) == 1


@pytest.mark.api
@pytest.mark.regression
class TestOAuth2ClientCredentials:
    def test_fetches_and_caches_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        token_requests = []

        def fake_post(
            url, data=None, timeout=None
        ):  # noqa: ANN001 - matches httpx.post signature loosely
            token_requests.append(data)
            return httpx.Response(
                200,
                json={"access_token": "tok-1", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer tok-1"
            return httpx.Response(200)

        auth = OAuth2ClientCredentialsAuth("http://idp/token", "client-id", "client-secret")
        with _client_for(auth, handler) as client:
            client.get("/x")
            client.get("/y")  # second call must reuse the cached token, not re-fetch

        assert len(token_requests) == 1
        assert token_requests[0]["grant_type"] == "client_credentials"

    def test_token_fetch_failure_raises_authentication_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                400, json={"error": "invalid_client"}, request=httpx.Request("POST", url)
            )

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        auth = OAuth2ClientCredentialsAuth("http://idp/token", "bad-id", "bad-secret")
        with pytest.raises(ApiAuthenticationError), _client_for(auth, handler) as client:
            client.get("/x")


@pytest.mark.api
@pytest.mark.regression
class TestAuthFactory:
    def test_builds_no_auth(self) -> None:
        config = ApiEndpointConfig(base_url="http://x", auth_type="none")
        assert isinstance(AuthFactory.from_config(config), NoAuth)

    def test_builds_basic_auth(self) -> None:
        config = ApiEndpointConfig(
            base_url="http://x", auth_type="basic", client_id="u", client_secret="p"
        )
        assert isinstance(AuthFactory.from_config(config), BasicAuthStrategy)

    def test_builds_api_key_auth(self) -> None:
        config = ApiEndpointConfig(base_url="http://x", auth_type="api_key", api_key="k")
        assert isinstance(AuthFactory.from_config(config), ApiKeyAuth)

    def test_builds_oauth2_client_credentials_when_token_url_set(self) -> None:
        config = ApiEndpointConfig(
            base_url="http://x",
            auth_type="oauth2",
            token_url="http://idp/token",
            client_id="id",
            client_secret="secret",
        )
        assert isinstance(AuthFactory.from_config(config), OAuth2ClientCredentialsAuth)

    def test_oauth2_without_token_url_raises(self) -> None:
        config = ApiEndpointConfig(base_url="http://x", auth_type="oauth2")
        with pytest.raises(ConfigurationError, match="token_url"):
            AuthFactory.from_config(config)

    def test_bearer_requires_manual_construction(self) -> None:
        config = ApiEndpointConfig(base_url="http://x", auth_type="bearer")
        with pytest.raises(ConfigurationError, match="runtime-obtained"):
            AuthFactory.from_config(config)

    def test_mtls_raises_transport_level_error(self) -> None:
        config = ApiEndpointConfig(base_url="http://x", auth_type="mtls")
        with pytest.raises(ConfigurationError, match="transport-level"):
            AuthFactory.from_config(config)

    def test_unknown_auth_type_raises(self) -> None:
        config = ApiEndpointConfig.model_construct(
            base_url="http://x",
            auth_type="nonsense",
            client_id="",
            client_secret="",
            api_key="",
            timeout_seconds=30,
            token_url=None,
        )
        with pytest.raises(ConfigurationError, match="Unknown auth_type"):
            AuthFactory.from_config(config)
