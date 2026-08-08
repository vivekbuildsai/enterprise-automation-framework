from __future__ import annotations

from playwright.sync_api import Page

from framework.pages.policy_management import PolicyData, PolicyManagementPage


class PolicyCreationWorkflow:
    """Skeleton workflow — composes navigation + `PolicyManagementPage.create_policy()`.
    Real code, but exercising it end-to-end needs a real target application
    (see `framework/pages/policy_management/page.py`); wire up
    `tests/e2e/policy_management` once real selectors/environment are available.
    """

    def __init__(self, page: Page, *, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def execute(self, policy: PolicyData) -> None:
        policy_page = PolicyManagementPage(self.page)
        policy_page.base_url = self.base_url
        policy_page.open()
        policy_page.create_policy(policy.name, policy.policy_type)
