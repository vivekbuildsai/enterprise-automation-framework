import datetime
from typing import Any

import httpx
import pytest

from framework.api.exceptions import ApiResponseValidationError, ApiSchemaValidationError
from framework.api.validators import ResponseValidator


def _make_response(
    status_code: int = 200,
    *,
    json: Any = None,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    elapsed_ms: float = 10,
) -> httpx.Response:
    response = httpx.Response(
        status_code,
        json=json,
        headers=headers or {},
        request=httpx.Request("GET", "http://test/resource"),
    )
    if cookies:
        for name, value in cookies.items():
            response.headers["set-cookie"] = f"{name}={value}"
    response.elapsed = datetime.timedelta(milliseconds=elapsed_ms)
    return response


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorStatus:
    def test_expect_status_passes_on_match(self) -> None:
        ResponseValidator(_make_response(200)).expect_status(200)

    def test_expect_status_accepts_a_set_of_allowed_codes(self) -> None:
        ResponseValidator(_make_response(201)).expect_status({200, 201})

    def test_expect_status_fails_on_mismatch(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="404"):
            ResponseValidator(_make_response(404)).expect_status(200)


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorHeaders:
    def test_expect_header_present(self) -> None:
        ResponseValidator(_make_response(200, headers={"X-Trace": "abc"})).expect_header("X-Trace")

    def test_expect_header_with_value(self) -> None:
        ResponseValidator(_make_response(200, headers={"X-Trace": "abc"})).expect_header(
            "X-Trace", "abc"
        )

    def test_expect_header_missing_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError):
            ResponseValidator(_make_response(200)).expect_header("X-Trace")

    def test_expect_header_wrong_value_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError):
            ResponseValidator(_make_response(200, headers={"X-Trace": "abc"})).expect_header(
                "X-Trace", "xyz"
            )


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorTiming:
    def test_expect_response_time_under_passes(self) -> None:
        ResponseValidator(_make_response(200, elapsed_ms=50)).expect_response_time_under(1000)

    def test_expect_response_time_under_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="Response time"):
            ResponseValidator(_make_response(200, elapsed_ms=5000)).expect_response_time_under(1000)


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorJsonFields:
    def test_expect_json_field_simple(self) -> None:
        ResponseValidator(_make_response(json={"username": "ada"})).expect_json_field(
            "username", "ada"
        )

    def test_expect_json_field_nested(self) -> None:
        ResponseValidator(
            _make_response(json={"user": {"address": {"city": "London"}}})
        ).expect_json_field("user.address.city", "London")

    def test_expect_json_field_collection_index(self) -> None:
        ResponseValidator(_make_response(json={"users": [{"id": 1}, {"id": 2}]})).expect_json_field(
            "users.1.id", 2
        )

    def test_expect_json_field_wrong_value_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError):
            ResponseValidator(_make_response(json={"username": "ada"})).expect_json_field(
                "username", "wrong"
            )

    def test_expect_json_field_missing_fails_with_path_in_message(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="user.email"):
            ResponseValidator(_make_response(json={"user": {}})).expect_json_field_present(
                "user.email"
            )

    def test_chaining_returns_self_for_fluent_use(self) -> None:
        result = (
            ResponseValidator(_make_response(200, json={"a": 1}))
            .expect_status(200)
            .expect_json_field("a", 1)
        )
        assert isinstance(result, ResponseValidator)


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorCollections:
    def test_expect_collection_size_exact(self) -> None:
        ResponseValidator(_make_response(json={"items": [1, 2, 3]})).expect_collection_size(
            "items", exact=3
        )

    def test_expect_collection_size_min_max(self) -> None:
        ResponseValidator(_make_response(json={"items": [1, 2, 3]})).expect_collection_size(
            "items", min_size=1, max_size=5
        )

    def test_expect_collection_size_wrong_exact_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError):
            ResponseValidator(_make_response(json={"items": [1, 2]})).expect_collection_size(
                "items", exact=3
            )

    def test_expect_collection_size_not_a_list_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="expected a list"):
            ResponseValidator(_make_response(json={"items": {"a": 1}})).expect_collection_size(
                "items", exact=1
            )

    def test_expect_collection_size_below_min_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="at least"):
            ResponseValidator(_make_response(json={"items": [1]})).expect_collection_size(
                "items", min_size=3
            )

    def test_expect_collection_size_above_max_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="at most"):
            ResponseValidator(_make_response(json={"items": [1, 2, 3]})).expect_collection_size(
                "items", max_size=1
            )


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorCookies:
    def test_expect_cookie_present(self) -> None:
        ResponseValidator(_make_response(200, cookies={"session": "abc"})).expect_cookie("session")

    def test_expect_cookie_with_value(self) -> None:
        ResponseValidator(_make_response(200, cookies={"session": "abc"})).expect_cookie(
            "session", "abc"
        )

    def test_expect_cookie_missing_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError, match="not present"):
            ResponseValidator(_make_response(200)).expect_cookie("session")

    def test_expect_cookie_wrong_value_fails(self) -> None:
        with pytest.raises(ApiResponseValidationError):
            ResponseValidator(_make_response(200, cookies={"session": "abc"})).expect_cookie(
                "session", "xyz"
            )


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorMisc:
    def test_response_time_check_is_skipped_when_elapsed_unavailable(self) -> None:
        import httpx as httpx_module

        response = httpx_module.Response(
            200, json={"a": 1}, request=httpx_module.Request("GET", "http://x/")
        )
        # No .elapsed set (as with an httpx.MockTransport response) — must not raise.
        ResponseValidator(response).expect_response_time_under(1000)

    def test_json_escape_hatch_returns_parsed_body(self) -> None:
        validator = ResponseValidator(_make_response(json={"a": 1, "b": [1, 2]}))
        assert validator.json() == {"a": 1, "b": [1, 2]}


@pytest.mark.api
@pytest.mark.regression
class TestResponseValidatorSchema:
    def test_expect_schema_passes_on_valid_body(self) -> None:
        ResponseValidator(_make_response(json={"id": 1, "firstName": "Ada"})).expect_schema(
            "user_schema"
        )

    def test_expect_schema_fails_on_invalid_body(self) -> None:
        with pytest.raises(ApiSchemaValidationError):
            ResponseValidator(_make_response(json={"firstName": "Ada"})).expect_schema(
                "user_schema"
            )
