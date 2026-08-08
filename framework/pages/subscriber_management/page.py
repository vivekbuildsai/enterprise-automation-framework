from __future__ import annotations

from playwright.sync_api import Page

from framework.components import TableComponent
from framework.pages.base_page import BasePage


class SubscriberManagementPage(BasePage):
    """Subscriber search/list screen. No specific real target application
    is bundled with this framework, so this targets the-internet.herokuapp.com's `/tables`
    demo as a stand-in data grid — same convention Milestone 1 used for
    Login/Dashboard. `search_subscriber` does a client-side lookup against
    the loaded table (the demo has no server-side search) — swap the body
    for a real search-box interaction once the actual app's search endpoint
    exists; the method signature (business action in, structured result
    out) shouldn't need to change.
    """

    path = "/tables"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.table = TableComponent(page, "#table1")

    def subscriber_count(self) -> int:
        return self.table.row_count()

    def search_subscriber(self, last_name: str) -> dict[str, str] | None:
        """Returns the matching subscriber row as a header-keyed dict, or
        `None` if no subscriber with that last name is present.
        """
        row_index = self.table.find_row_index(last_name)
        if row_index is None:
            return None
        headers = self.table.headers()
        values = self.table.rows()[row_index]
        return dict(zip(headers, values, strict=True))

    def edit_subscriber(self, last_name: str) -> None:
        row_index = self.table.find_row_index(last_name)
        if row_index is None:
            raise ValueError(f"No subscriber found with last name '{last_name}'")
        self.table.click_row_action(row_index, "edit")

    def delete_subscriber(self, last_name: str) -> None:
        row_index = self.table.find_row_index(last_name)
        if row_index is None:
            raise ValueError(f"No subscriber found with last name '{last_name}'")
        self.table.click_row_action(row_index, "delete")
