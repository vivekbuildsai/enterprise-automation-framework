import pytest

from framework.exceptions import ConfigurationError


@pytest.mark.api
@pytest.mark.regression
class TestApiClientFixtureConfigValidation:
    @pytest.fixture
    def api_service_key(self) -> str:
        return "this_service_does_not_exist_in_any_environment_yaml"

    def test_api_client_fixture_raises_clear_error_for_unknown_service_key(
        self, request: pytest.FixtureRequest
    ) -> None:
        # Requesting the fixture on demand (rather than as a test parameter) lets
        # us assert on the setup-time error it raises instead of that error
        # aborting the test as a setup failure.
        with pytest.raises(
            ConfigurationError, match="this_service_does_not_exist_in_any_environment_yaml"
        ):
            request.getfixturevalue("api_client")
