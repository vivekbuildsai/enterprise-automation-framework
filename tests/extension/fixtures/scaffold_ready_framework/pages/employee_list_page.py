from playwright.sync_api import Page


class EmployeeListPage:
    """An existing Page Object for the existing UI — evidence this
    customer's own framework is already Python + Playwright.
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> None:
        self.page.goto("/employees")
