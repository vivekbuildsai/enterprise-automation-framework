import httpx
import pytest

from framework.api.builders import RequestBuilder
from framework.api.client import ApiClient
from framework.api.exceptions import ApiConnectionError, ApiTimeoutError


def _client_with_transport(handler) -> ApiClient:
    return ApiClient("http://test", transport=httpx.MockTransport(handler))


@pytest.mark.api
@pytest.mark.regression
class TestApiClientVerbs:
    @pytest.mark.parametrize("verb", ["get", "post", "put", "patch", "delete", "head", "options"])
    def test_every_verb_sends_the_matching_http_method(self, verb: str) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["method"] = request.method
            return httpx.Response(200)

        client = _client_with_transport(handler)
        getattr(client, verb)("/x")
        client.close()

        assert seen["method"] == verb.upper()

    def test_path_params_and_query_params_and_json_body_are_sent(self) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["body"] = request.content
            return httpx.Response(200)

        client = _client_with_transport(handler)
        client.post(
            "/users/{id}", path_params={"id": 7}, query_params={"verbose": "1"}, json={"a": 1}
        )
        client.close()

        assert seen["url"] == "http://test/users/7?verbose=1"
        assert seen["body"] == b'{"a": 1}'

    def test_request_method_executes_a_prebuilt_request_builder(self) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["method"] = request.method
            seen["body"] = request.content
            return httpx.Response(200)

        client = _client_with_transport(handler)
        builder = RequestBuilder("POST", "/upload").multipart({"file": ("a.txt", b"hello")})
        client.request(builder)
        client.close()

        assert seen["method"] == "POST"
        assert b"hello" in seen["body"]


@pytest.mark.api
@pytest.mark.regression
class TestApiClientRetry:
    @pytest.fixture(autouse=True)
    def _no_real_backoff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # These tests assert retry *behavior* (attempt counts, final status),
        # not tenacity's actual exponential-backoff timing — real sleeps here
        # only make the suite slower without covering anything additional.
        monkeypatch.setattr("time.sleep", lambda _seconds: None)

    def test_get_retries_on_503_then_succeeds(self) -> None:
        responses = iter(
            [httpx.Response(503), httpx.Response(503), httpx.Response(200, json={"ok": True})]
        )
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return next(responses)

        client = _client_with_transport(handler)
        response = client.get("/flaky")
        client.close()

        assert response.status_code == 200
        assert len(attempts) == 3

    def test_get_gives_up_after_max_attempts_on_persistent_503(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = _client_with_transport(handler)
        response = client.get("/always-down")
        client.close()

        assert response.status_code == 503  # retries exhausted, last response returned as-is

    def test_post_is_not_retried_on_503(self) -> None:
        """POST is not in RetryPolicy.SAFE_METHODS — retrying a non-idempotent
        call automatically could duplicate a side effect, so exactly one
        attempt is made regardless of status code.
        """
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return httpx.Response(503)

        client = _client_with_transport(handler)
        client.post("/create", json={"a": 1})
        client.close()

        assert len(attempts) == 1

    def test_unsafe_method_transient_error_is_translated_without_retry(self) -> None:
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            raise httpx.ConnectError("boom", request=request)

        client = _client_with_transport(handler)
        with pytest.raises(ApiConnectionError):
            client.post("/create", json={"a": 1})
        client.close()

        assert (
            len(attempts) == 1
        )  # POST is unsafe — one attempt, but still translated to an Api*Error

    def test_read_timeout_is_translated_to_api_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        client = _client_with_transport(handler)
        with pytest.raises(ApiTimeoutError):
            client.get("/slow")
        client.close()

    def test_connect_error_is_translated_and_retried(self) -> None:
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            raise httpx.ConnectError("boom", request=request)

        client = _client_with_transport(handler)
        with pytest.raises(ApiConnectionError):
            client.get("/unreachable")
        client.close()

        assert len(attempts) == 3  # RetryPolicy.MAX_ATTEMPTS

    def test_non_retryable_status_is_returned_immediately(self) -> None:
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(1)
            return httpx.Response(404)

        client = _client_with_transport(handler)
        response = client.get("/missing")
        client.close()

        assert response.status_code == 404
        assert len(attempts) == 1


@pytest.mark.api
@pytest.mark.regression
class TestApiClientContextManager:
    def test_context_manager_closes_client(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        with _client_with_transport(handler) as client:
            client.get("/x")
        # closing twice must not raise
        client.close()
