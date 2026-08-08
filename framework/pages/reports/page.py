from __future__ import annotations

from framework.pages.base_page import BasePage

# Skeleton module — see framework/pages/policy_management/page.py for the
# convention this follows.


class ReportsPage(BasePage):
    path = "/reports"

    REPORT_TYPE_SELECT = "[data-testid='report-type-select']"
    DATE_FROM_INPUT = "[data-testid='report-date-from']"
    DATE_TO_INPUT = "[data-testid='report-date-to']"
    GENERATE_BUTTON = "[data-testid='report-generate-button']"
    EXPORT_BUTTON = "[data-testid='report-export-button']"
    LOADER = "[data-testid='report-loading']"

    def generate_report(self, report_type: str, date_from: str, date_to: str) -> None:
        self.select_option(self.REPORT_TYPE_SELECT, report_type, description="Report type")
        self.fill(self.DATE_FROM_INPUT, date_from, description="Report date from")
        self.fill(self.DATE_TO_INPUT, date_to, description="Report date to")
        self.click(self.GENERATE_BUTTON, description="Generate report")
        self.wait_for_loader_gone(self.LOADER)

    def export_report(self, save_path: str) -> None:
        self.download_file(self.EXPORT_BUTTON, save_path, description="Export report")
