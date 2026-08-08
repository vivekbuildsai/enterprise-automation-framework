from __future__ import annotations

from framework.pages.base_page import BasePage

# Skeleton module — see framework/pages/policy_management/page.py for the
# convention this follows (placeholder data-testid selectors, real business
# logic, update selectors once a real target application is available).


class AlarmManagementPage(BasePage):
    path = "/alarms"

    SEVERITY_FILTER = "[data-testid='alarm-severity-filter']"
    ROW_TEMPLATE = "[data-testid='alarm-row-{alarm_id}']"
    APPROVE_BUTTON_TEMPLATE = (
        "[data-testid='alarm-row-{alarm_id}'] [data-testid='alarm-approve-button']"
    )
    ACKNOWLEDGE_BUTTON_TEMPLATE = (
        "[data-testid='alarm-row-{alarm_id}'] [data-testid='alarm-acknowledge-button']"
    )
    STATUS_TEMPLATE = "[data-testid='alarm-row-{alarm_id}'] [data-testid='alarm-status']"

    def filter_by_severity(self, severity: str) -> None:
        self.select_option(self.SEVERITY_FILTER, severity, description="Alarm severity filter")

    def approve_alarm(self, alarm_id: str) -> None:
        self.click_and_wait_for_toast(
            self.APPROVE_BUTTON_TEMPLATE.format(alarm_id=alarm_id),
            description=f"Approve alarm {alarm_id}",
        )

    def acknowledge_alarm(self, alarm_id: str) -> None:
        self.click_and_wait_for_toast(
            self.ACKNOWLEDGE_BUTTON_TEMPLATE.format(alarm_id=alarm_id),
            description=f"Acknowledge alarm {alarm_id}",
        )

    def alarm_status(self, alarm_id: str) -> str:
        return self.get_text(
            self.STATUS_TEMPLATE.format(alarm_id=alarm_id), description=f"Alarm {alarm_id} status"
        )
