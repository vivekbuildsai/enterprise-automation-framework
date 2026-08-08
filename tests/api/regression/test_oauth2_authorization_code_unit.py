import httpx
import pytest

from framework.api.auth import OAuth2AuthorizationCodeAuth
from framework.api.exceptions import ApiAuthenticationError


def _client_for(auth: httpx.Auth, handler) -> httpx.Client:
    return httpx.Client(base_url="http://test", auth=auth, transport=httpx.MockTransport(handler))


def _token_response(url: str, **fields: object) -> httpx.Response:
    body = {"access_token": "tok-1", "expires_in": 3600, **fields}
    return httpx.Response(200, json=body, request=httpx.Request("POST", url))


@pytest.mark.api
@pytest.mark.regression
class TestOAuth2AuthorizationCode:
    def test_exchanges_code_for_token_on_first_use(self, monkeypatch: pytest.MonkeyPatch) -> None:
        token_requests = []

        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            token_requests.append(data)
            return _token_response(url)

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer tok-1"
            return httpx.Response(200)

        auth = OAuth2AuthorizationCodeAuth(
            "http://idp/token", "client-id", "client-secret", "http://app/callback", "auth-code-123"
        )
        with _client_for(auth, handler) as client:
            client.get("/x")

        assert token_requests[0]["grant_type"] == "authorization_code"
        assert token_requests[0]["code"] == "auth-code-123"

    def test_reuses_cached_token_within_expiry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        call_count = {"n": 0}

        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            call_count["n"] += 1
            return _token_response(url)

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        auth = OAuth2AuthorizationCodeAuth("http://idp/token", "id", "secret", "http://cb", "code")
        with _client_for(auth, handler) as client:
            client.get("/x")
            client.get("/y")

        assert call_count["n"] == 1

    def test_refreshes_with_refresh_token_when_expired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = []

        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            calls.append(data["grant_type"])
            if data["grant_type"] == "authorization_code":
                return _token_response(url, expires_in=-1, refresh_token="refresh-1")
            return _token_response(url, access_token="tok-2")

        monkeypatch.setattr(httpx, "post", fake_post)
        seen_tokens = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_tokens.append(request.headers["Authorization"])
            return httpx.Response(200)

        auth = OAuth2AuthorizationCodeAuth("http://idp/token", "id", "secret", "http://cb", "code")
        with _client_for(auth, handler) as client:
            client.get("/x")  # exchanges code, token immediately "expired" (expires_in=-1)
            client.get("/y")  # must refresh before this call

        assert calls == ["authorization_code", "refresh_token"]
        assert seen_tokens == ["Bearer tok-1", "Bearer tok-2"]

    def test_expired_without_refresh_token_keeps_using_stale_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = []

        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            calls.append(data["grant_type"])
            return _token_response(url, expires_in=-1)  # no refresh_token issued

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        auth = OAuth2AuthorizationCodeAuth("http://idp/token", "id", "secret", "http://cb", "code")
        with _client_for(auth, handler) as client:
            client.get("/x")
            client.get("/y")

        assert calls == ["authorization_code"]  # no refresh attempted, no refresh_token to use

    def test_token_exchange_failure_raises_authentication_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_post(url, data=None, timeout=None):  # noqa: ANN001
            return httpx.Response(
                400, json={"error": "invalid_grant"}, request=httpx.Request("POST", url)
            )

        monkeypatch.setattr(httpx, "post", fake_post)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        auth = OAuth2AuthorizationCodeAuth(
            "http://idp/token", "id", "secret", "http://cb", "bad-code"
        )
        with pytest.raises(ApiAuthenticationError), _client_for(auth, handler) as client:
            client.get("/x")
