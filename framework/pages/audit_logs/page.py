from __future__ import annotations

from playwright.sync_api import Page

from framework.components import TableComponent
from framework.pages.base_page import BasePage

# Skeleton module — see framework/pages/policy_management/page.py for the
# convention this follows.


class AuditLogsPage(BasePage):
    path = "/audit-logs"

    USER_FILTER_INPUT = "[data-testid='audit-user-filter']"
    DATE_FROM_INPUT = "[data-testid='audit-date-from']"
    DATE_TO_INPUT = "[data-testid='audit-date-to']"
    SEARCH_BUTTON = "[data-testid='audit-search-button']"
    EXPORT_BUTTON = "[data-testid='audit-export-button']"
    TABLE_SELECTOR = "[data-testid='audit-log-table']"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.log_table = TableComponent(page, self.TABLE_SELECTOR)

    def search_logs(self, *, user: str = "", date_from: str = "", date_to: str = "") -> None:
        if user:
            self.fill(self.USER_FILTER_INPUT, user, description="Audit user filter")
        if date_from:
            self.fill(self.DATE_FROM_INPUT, date_from, description="Audit date from")
        if date_to:
            self.fill(self.DATE_TO_INPUT, date_to, description="Audit date to")
        self.click(self.SEARCH_BUTTON, description="Search audit logs")

    def export_logs(self, save_path: str) -> None:
        self.download_file(self.EXPORT_BUTTON, save_path, description="Export audit logs")

    def log_entries(self) -> list[list[str]]:
        return self.log_table.rows()
