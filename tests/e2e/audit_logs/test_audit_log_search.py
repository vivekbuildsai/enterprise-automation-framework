import allure
import pytest

from framework.pages.audit_logs import AuditLogAssertions, AuditLogsPage, AuditLogTestDataBuilder

pytestmark = pytest.mark.skip(
    reason="Audit Logs is a skeleton module — no real target application environment is "
    "reachable to run this against. Structure is real; remove this skip once real "
    "selectors + a target environment exist."
)


@allure.feature("Audit Logs")
@pytest.mark.ui
@pytest.mark.e2e
class TestAuditLogSearch:
    def test_search_logs_for_user(self, page, settings) -> None:
        criteria = AuditLogTestDataBuilder.last_7_days_for_user("admin")
        audit_page = AuditLogsPage(page)
        audit_page.base_url = str(settings.ui.base_url)
        audit_page.open()

        with allure.step("Search audit logs for the last 7 days for 'admin'"):
            audit_page.search_logs(
                user=criteria.user, date_from=criteria.date_from, date_to=criteria.date_to
            )

        with allure.step("Verify results reference the searched user"):
            AuditLogAssertions.entry_contains(audit_page.log_entries(), "admin")
