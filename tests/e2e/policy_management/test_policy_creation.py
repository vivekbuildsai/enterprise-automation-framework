import allure
import pytest

from framework.pages.policy_management import (
    PolicyAssertions,
    PolicyManagementPage,
    PolicyTestDataBuilder,
)
from framework.workflows import PolicyCreationWorkflow

pytestmark = pytest.mark.skip(
    reason="Policy Management is a skeleton module — no real target application environment "
    "is reachable to run this against. Structure (page/workflow/assertions/test data) "
    "is real; remove this skip once real selectors + a target environment exist."
)


@allure.feature("Policy Management")
@pytest.mark.ui
@pytest.mark.e2e
class TestPolicyCreation:
    def test_create_policy_sets_status_active(self, page, settings) -> None:
        policy = PolicyTestDataBuilder.random_policy()

        with allure.step(f"Create policy '{policy.name}'"):
            PolicyCreationWorkflow(page, base_url=str(settings.ui.base_url)).execute(policy)

        with allure.step("Verify the policy is active"):
            status = PolicyManagementPage(page).policy_status(policy.name)
            PolicyAssertions.status_is(status, "Active", policy.name)
