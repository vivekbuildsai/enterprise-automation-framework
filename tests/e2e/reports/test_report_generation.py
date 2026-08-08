import allure
import pytest

from framework.assertions import UIAssert
from framework.pages.reports import ReportsPage, ReportTestDataBuilder

pytestmark = pytest.mark.skip(
    reason="Reports is a skeleton module — no real target application environment is "
    "reachable to run this against. Structure is real; remove this skip once real "
    "selectors + a target environment exist."
)


@allure.feature("Reports")
@pytest.mark.ui
@pytest.mark.e2e
class TestReportGeneration:
    def test_generate_and_export_report(self, page, settings, tmp_path) -> None:
        request = ReportTestDataBuilder.last_30_days()
        reports_page = ReportsPage(page)
        reports_page.base_url = str(settings.ui.base_url)
        reports_page.open()

        with allure.step("Generate a 30-day usage summary report"):
            reports_page.generate_report(request.report_type, request.date_from, request.date_to)

        with allure.step("Export it and verify the download succeeded"):
            save_path = tmp_path / "report.csv"
            reports_page.export_report(str(save_path))
            UIAssert.download_success(save_path)
