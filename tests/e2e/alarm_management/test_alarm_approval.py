import allure
import pytest

from framework.pages.alarm_management import AlarmAssertions, AlarmManagementPage

pytestmark = pytest.mark.skip(
    reason="Alarm Management is a skeleton module — no real target application environment "
    "is reachable to run this against. Structure is real; remove this skip once real "
    "selectors + a target environment exist."
)


@allure.feature("Alarm Management")
@pytest.mark.ui
@pytest.mark.e2e
class TestAlarmApproval:
    def test_approve_alarm_sets_status_approved(self, page, settings) -> None:
        alarm_page = AlarmManagementPage(page)
        alarm_page.base_url = str(settings.ui.base_url)
        alarm_page.open()

        with allure.step("Approve alarm ALM-1001"):
            alarm_page.approve_alarm("ALM-1001")

        with allure.step("Verify status is Approved"):
            AlarmAssertions.status_is(alarm_page.alarm_status("ALM-1001"), "Approved", "ALM-1001")
