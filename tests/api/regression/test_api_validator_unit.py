import httpx
import pytest

from framework.api.client import ApiClient
from framework.api.exceptions import ApiResponseValidationError
from framework.api.services import ApiValidator


def _validator_with(handler) -> ApiValidator:
    client = ApiClient("http://test", transport=httpx.MockTransport(handler))
    return ApiValidator(client)


@pytest.mark.api
@pytest.mark.regression
class TestApiValidator:
    def test_verify_login_returns_parsed_response_on_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "username": "ada",
                    "email": "ada@example.com",
                    "firstName": "Ada",
                    "lastName": "Lovelace",
                    "accessToken": "tok",
                    "refreshToken": "ref",
                },
            )

        login = _validator_with(handler).verify_login("ada", "pw")
        assert login.username == "ada"

    def test_verify_login_raises_response_validation_error_when_status_is_not_200(self) -> None:
        # Status is asserted *before* parsing, so a rejected login raises the
        # clear ApiResponseValidationError below — not a confusing "field
        # required" Pydantic error from trying to parse the error body as a
        # successful login response.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"message": "Invalid credentials"})

        with pytest.raises(ApiResponseValidationError):
            _validator_with(handler).verify_login("ada", "wrong")

    def test_verify_user_exists_returns_user_on_200(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": 2, "firstName": "Michael"})

        user = _validator_with(handler).verify_user_exists(2)
        assert user.id == 2

    def test_verify_user_exists_raises_on_404(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"message": "not found"})

        with pytest.raises(ApiResponseValidationError):
            _validator_with(handler).verify_user_exists(999)

    def test_verify_user_field_matches_expected_value(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": 2, "firstName": "Michael"})

        user = _validator_with(handler).verify_user_field(2, "firstName", "Michael")
        assert user.first_name == "Michael"

    def test_verify_user_field_raises_on_mismatch(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": 2, "firstName": "Michael"})

        with pytest.raises(ApiResponseValidationError):
            _validator_with(handler).verify_user_field(2, "firstName", "SomeoneElse")
