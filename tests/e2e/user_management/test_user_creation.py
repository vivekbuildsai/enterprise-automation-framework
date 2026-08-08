import allure
import pytest

from framework.pages.user_management import (
    UserManagementAssertions,
    UserManagementPage,
    UserManagementTestDataBuilder,
)
from framework.workflows import UserCreationWorkflow

pytestmark = pytest.mark.skip(
    reason="User Management is a skeleton module — no real target application environment "
    "is reachable to run this against. Structure (page/workflow/assertions/test data) "
    "is real; remove this skip once real selectors + a target environment exist."
)


@allure.feature("User Management")
@pytest.mark.ui
@pytest.mark.e2e
class TestUserCreation:
    def test_create_user_assigns_role(self, page, settings) -> None:
        new_user = UserManagementTestDataBuilder.random_user(role="Editor")

        with allure.step(f"Create user '{new_user.username}'"):
            UserCreationWorkflow(page, base_url=str(settings.ui.base_url)).execute(new_user)

        with allure.step("Verify the assigned role"):
            role = UserManagementPage(page).user_role(new_user.username)
            UserManagementAssertions.role_is(role, "Editor", new_user.username)
