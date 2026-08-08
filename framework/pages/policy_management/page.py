from __future__ import annotations

from framework.pages.base_page import BasePage

# Skeleton module: no specific real target application is reachable from
# this environment, so these are the best-guess data-testid conventions this framework uses
# elsewhere (see Locators strategy) rather than verified real selectors.
# Update the constants below once the real app's markup is available —
# callers of these business-action methods shouldn't need to change.


class PolicyManagementPage(BasePage):
    path = "/policies"

    POLICY_NAME_INPUT = "[data-testid='policy-name-input']"
    POLICY_TYPE_SELECT = "[data-testid='policy-type-select']"
    CREATE_BUTTON = "[data-testid='policy-create-button']"
    SEARCH_INPUT = "[data-testid='policy-search-input']"
    DELETE_BUTTON_TEMPLATE = (
        "[data-testid='policy-row-{name}'] [data-testid='policy-delete-button']"
    )
    STATUS_TEMPLATE = "[data-testid='policy-row-{name}'] [data-testid='policy-status']"

    def create_policy(self, name: str, policy_type: str) -> None:
        self.fill(self.POLICY_NAME_INPUT, name, description="Policy name")
        self.select_option(self.POLICY_TYPE_SELECT, policy_type, description="Policy type")
        self.click_and_wait_for_toast(self.CREATE_BUTTON, description="Create policy")

    def delete_policy(self, name: str) -> None:
        self.click_and_wait_for_toast(
            self.DELETE_BUTTON_TEMPLATE.format(name=name), description=f"Delete policy '{name}'"
        )

    def search_policy(self, name: str) -> None:
        self.fill(self.SEARCH_INPUT, name, description="Policy search")
        self.press_key("Enter", selector=self.SEARCH_INPUT)

    def policy_status(self, name: str) -> str:
        return self.get_text(
            self.STATUS_TEMPLATE.format(name=name), description=f"Policy '{name}' status"
        )
