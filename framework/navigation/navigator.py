from __future__ import annotations

from playwright.sync_api import Page

from framework.components import BreadcrumbComponent, SidebarComponent, TopNavigationComponent
from framework.logger import get_logger


class AppNavigator:
    """Composes `SidebarComponent`/`TopNavigationComponent` into a single
    "get me to module X" entry point, so Workflows and tests navigate by
    business-module name (`navigator.go_to("Subscriber Management")`)
    instead of each Page Object re-implementing "click the right sidebar
    item" — the Navigation Layer sitting between raw Components and the
    Workflow Layer.
    """

    def __init__(
        self,
        page: Page,
        *,
        base_url: str = "",
        sidebar: SidebarComponent | None = None,
        top_navigation: TopNavigationComponent | None = None,
        breadcrumb: BreadcrumbComponent | None = None,
    ) -> None:
        self.page = page
        self.base_url = base_url
        self.sidebar = sidebar or SidebarComponent(page)
        self.top_navigation = top_navigation
        self.breadcrumb = breadcrumb
        self._logger = get_logger("AppNavigator")

    def go_to_module(self, module_name: str) -> None:
        """Navigate via the sidebar — the primary way a module is reached."""
        self._logger.info(f"Navigating to module '{module_name}'")
        self.sidebar.click_item(module_name)
        self.page.wait_for_load_state("domcontentloaded")

    def go_to_tab(self, tab_name: str) -> None:
        """Navigate via the top-nav tabs — for switching sub-views within
        the currently-open module.
        """
        if self.top_navigation is None:
            raise RuntimeError("AppNavigator was constructed without a TopNavigationComponent")
        self._logger.info(f"Navigating to tab '{tab_name}'")
        self.top_navigation.click_tab(tab_name)

    def go_to_url(self, path: str) -> None:
        """Direct navigation by URL — for deep links or when no nav
        component reaches a page (e.g. landing straight on a detail view).
        """
        target = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if self.base_url else path
        self._logger.info(f"Navigating directly to '{target}'")
        self.page.goto(target)

    def current_breadcrumb_trail(self) -> list[str]:
        if self.breadcrumb is None:
            raise RuntimeError("AppNavigator was constructed without a BreadcrumbComponent")
        return self.breadcrumb.items()
