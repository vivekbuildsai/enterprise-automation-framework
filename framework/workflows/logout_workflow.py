from __future__ import annotations

from framework.pages import DashboardPage, LoginPage


class LogoutWorkflow:
    """Composes `DashboardPage.logout()` behind the same workflow-level
    naming convention as `LoginWorkflow`, so tests read symmetrically
    (`LoginWorkflow(...).execute(...)` / `LogoutWorkflow(...).execute()`)
    even though logout today only touches one Page Object — the moment a
    real app adds a "confirm logout" dialog, this is the only place that changes.
    """

    def __init__(self, dashboard_page: DashboardPage) -> None:
        self.dashboard_page = dashboard_page

    def execute(self) -> LoginPage:
        return self.dashboard_page.logout()
