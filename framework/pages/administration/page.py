from __future__ import annotations

from framework.pages.base_page import BasePage

# Skeleton module — see framework/pages/policy_management/page.py for the
# convention this follows.


class AdministrationPage(BasePage):
    path = "/administration"

    ROLE_NAME_INPUT = "[data-testid='role-name-input']"
    CREATE_ROLE_BUTTON = "[data-testid='role-create-button']"
    FEATURE_FLAG_TOGGLE_TEMPLATE = "[data-testid='feature-flag-{flag_name}']"
    SAVE_SETTINGS_BUTTON = "[data-testid='settings-save-button']"

    def create_role(self, role_name: str) -> None:
        self.fill(self.ROLE_NAME_INPUT, role_name, description="Role name")
        self.click_and_wait_for_toast(self.CREATE_ROLE_BUTTON, description="Create role")

    def toggle_feature_flag(self, flag_name: str) -> None:
        self.click(
            self.FEATURE_FLAG_TOGGLE_TEMPLATE.format(flag_name=flag_name),
            description=f"Toggle feature flag '{flag_name}'",
        )
        self.click_and_wait_for_toast(self.SAVE_SETTINGS_BUTTON, description="Save settings")
