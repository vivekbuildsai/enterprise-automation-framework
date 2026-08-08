from __future__ import annotations

from playwright.sync_api import Page

from framework.pages.user_management import NewUserData, UserManagementPage


class UserCreationWorkflow:
    """Skeleton workflow — see `PolicyCreationWorkflow` docstring; same
    "real code, no real app to run it against yet" status.
    """

    def __init__(self, page: Page, *, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def execute(self, user: NewUserData) -> None:
        user_page = UserManagementPage(self.page)
        user_page.base_url = self.base_url
        user_page.open()
        user_page.create_user(user.username, user.email, user.role)
