from __future__ import annotations

from collections.abc import Callable

from playwright.sync_api import Page


class UiCleanupHooks:
    """Optional page-driven cleanup actions — deliberately thin, since most
    real UI cleanup (e.g. deleting a record created through a form) is
    app-specific and belongs in the relevant page object. This covers only
    the handful of truly generic, cross-app actions.
    """

    @staticmethod
    def clear_storage(page: Page) -> None:
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")

    @staticmethod
    def clear_cookies(page: Page) -> None:
        page.context.clear_cookies()

    @staticmethod
    def logout_via(page: Page, logout_action: Callable[[Page], None]) -> None:
        """`logout_action` is page-object-specific (e.g. `lambda p:
        DashboardPage(p).logout()`) — this standardizes "logout is a
        cleanup step" without prescribing how logout itself works for a
        given app.
        """
        logout_action(page)
