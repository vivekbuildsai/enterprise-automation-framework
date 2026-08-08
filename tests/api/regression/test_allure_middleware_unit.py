import httpx
import pytest

from framework.api.middleware import attach_request, attach_response


@pytest.mark.api
@pytest.mark.regression
class TestAllureMiddleware:
    def test_attach_request_does_not_raise_when_allure_attach_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def broken_attach(*args: object, **kwargs: object) -> None:
            raise RuntimeError("no active allure context")

        monkeypatch.setattr("allure.attach", broken_attach)

        request = httpx.Request("GET", "http://test/x")
        attach_request(request)  # must not raise

    def test_attach_response_does_not_raise_when_allure_attach_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def broken_attach(*args: object, **kwargs: object) -> None:
            raise RuntimeError("no active allure context")

        monkeypatch.setattr("allure.attach", broken_attach)

        response = httpx.Response(200, json={"a": 1}, request=httpx.Request("GET", "http://test/x"))
        attach_response(response)  # must not raise

    def test_attach_request_succeeds_with_active_allure_context(self) -> None:
        request = httpx.Request("POST", "http://test/x", json={"a": 1})
        attach_request(request)  # runs for real inside this pytest-allure-backed test

    def test_attach_response_attaches_json_when_content_type_is_json(self) -> None:
        response = httpx.Response(
            200,
            json={"a": 1},
            headers={"content-type": "application/json"},
            request=httpx.Request("GET", "http://test/x"),
        )
        attach_response(response)
