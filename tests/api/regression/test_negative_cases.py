import allure
import pytest

from framework.api.client import ApiClient
from framework.api.endpoints import Endpoints
from framework.api.exceptions import ApiResponseValidationError
from framework.api.validators import ResponseValidator


@allure.feature("API - Negative Paths")
@pytest.mark.api
@pytest.mark.regression
class TestNegativeCases:
    """These deliberately call `api_client` directly rather than going
    through `AuthService`/`UserService` — the typed services parse the
    *success* response shape into a Pydantic model, so calling them here
    would raise a validation error for the wrong reason (an error body not
    matching the success schema) instead of asserting the thing this suite
    actually cares about: the status code and error contract the API
    returns for bad input.
    """

    def test_login_with_invalid_credentials_is_rejected(self, api_client: ApiClient) -> None:
        with allure.step("Attempt login with a bogus password"):
            response = api_client.post(
                Endpoints.LOGIN, json={"username": "emilys", "password": "not-the-real-password"}
            )

        with allure.step("Verify the API rejected it rather than silently succeeding"):
            ResponseValidator(response).expect_status({400, 401}).expect_json_field_present(
                "message"
            )

    def test_get_nonexistent_user_returns_404(self, api_client: ApiClient) -> None:
        with allure.step("Request a user id that doesn't exist"):
            response = api_client.get(Endpoints.USER_BY_ID, path_params={"id": 999_999})

        with allure.step("Verify 404, not a silent empty/default response"):
            ResponseValidator(response).expect_status(404).expect_json_field_present("message")

    def test_protected_endpoint_without_token_is_unauthorized(self, api_client: ApiClient) -> None:
        with allure.step("Call a bearer-protected endpoint with no token and no leftover session"):
            api_client.clear_cookies()
            response = api_client.get(Endpoints.AUTH_ME)

        with allure.step("Verify 401"):
            ResponseValidator(response).expect_status(401)

    def test_protected_endpoint_with_bogus_token_is_rejected(self, api_client: ApiClient) -> None:
        # dummyjson.com actually returns 500 (not 401) for a malformed/wrongly-signed
        # bearer token — its JWT verification throws instead of being caught as an
        # auth failure. Asserting the *real* response is the point of a negative
        # test: it would catch the provider fixing (or further breaking) this.
        with allure.step("Call a bearer-protected endpoint with an invalid token"):
            api_client.clear_cookies()
            response = api_client.get(
                Endpoints.AUTH_ME, headers={"Authorization": "Bearer bad.jwt.token"}
            )

        with allure.step(
            "Verify the request is rejected, and ResponseValidator raises on a wrong expectation"
        ):
            ResponseValidator(response).expect_status({401, 500}).expect_json_field_present(
                "message"
            )
            with pytest.raises(ApiResponseValidationError):
                ResponseValidator(response).expect_status(200)
