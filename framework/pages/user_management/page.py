from __future__ import annotations

from framework.pages.base_page import BasePage

# Skeleton module — see framework/pages/policy_management/page.py for the
# convention this follows.


class UserManagementPage(BasePage):
    path = "/users"

    USERNAME_INPUT = "[data-testid='user-username-input']"
    EMAIL_INPUT = "[data-testid='user-email-input']"
    ROLE_SELECT = "[data-testid='user-role-select']"
    CREATE_BUTTON = "[data-testid='user-create-button']"
    DELETE_BUTTON_TEMPLATE = (
        "[data-testid='user-row-{username}'] [data-testid='user-delete-button']"
    )
    ROLE_CELL_TEMPLATE = "[data-testid='user-row-{username}'] [data-testid='user-role-cell']"

    def create_user(self, username: str, email: str, role: str) -> None:
        self.fill(self.USERNAME_INPUT, username, description="Username")
        self.fill(self.EMAIL_INPUT, email, description="Email")
        self.select_option(self.ROLE_SELECT, role, description="Role")
        self.click_and_wait_for_toast(self.CREATE_BUTTON, description="Create user")

    def delete_user(self, username: str) -> None:
        self.click_and_wait_for_toast(
            self.DELETE_BUTTON_TEMPLATE.format(username=username),
            description=f"Delete user '{username}'",
        )

    def user_role(self, username: str) -> str:
        return self.get_text(
            self.ROLE_CELL_TEMPLATE.format(username=username), description=f"Role of '{username}'"
        )
