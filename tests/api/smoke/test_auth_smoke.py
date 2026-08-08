import allure
import pytest

from framework.api.services import ApiValidator, AuthService
from framework.api.validators import ResponseValidator


@allure.feature("API - Authentication")
@pytest.mark.api
@pytest.mark.smoke
class TestAuthSmoke:
    def test_login_with_valid_credentials_returns_tokens(self, auth_service: AuthService) -> None:
        with allure.step("Login with valid credentials"):
            login = auth_service.login("emilys", "emilyspass")

        with allure.step("Verify response and token payload"):
            ResponseValidator(auth_service.last_response).expect_status(
                200
            ).expect_response_time_under(5000).expect_schema("login_response_schema")
            assert login.username == "emilys"
            assert login.access_token
            assert login.refresh_token

    def test_bearer_token_grants_access_to_protected_endpoint(
        self, auth_service: AuthService
    ) -> None:
        login = auth_service.login("emilys", "emilyspass")

        with allure.step("Call a bearer-protected endpoint with the issued token"):
            current_user = auth_service.get_current_user(login.access_token)

        with allure.step("Verify the protected endpoint returns the logged-in user"):
            ResponseValidator(auth_service.last_response).expect_status(200)
            assert current_user.id == login.id
            assert current_user.username == login.username

    def test_api_validator_verifies_login(self, api_validator: ApiValidator) -> None:
        """Exercises the hybrid-validation-ready `ApiValidator` facade — the
        piece a future UI test would call to cross-check backend state (see
        `framework.api.services.api_validator` docstring).
        """
        with allure.step("Cross-check login via ApiValidator"):
            login = api_validator.verify_login("emilys", "emilyspass")

        assert login.username == "emilys"
