from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from framework.logger import get_logger

_logger = get_logger("Locators")

LocatorScope = Page | Locator
"""Anything a locator can be built relative to — the page itself (`BasePage`)
or a component's root element (`BaseComponent`). Both expose the same
`get_by_test_id`/`get_by_role`/`get_by_label`/`locator` methods Playwright
gives every scope, which is what makes components composable: a `Table`
inside a `Modal` builds locators the exact same way a page-level `Table`
does.
"""


class Locators:
    """Centralizes *how* a locator is built so every Page Object/Component
    follows the same priority order instead of each author picking
    whatever selector was easiest to copy from devtools:

        1. data-testid  — stable, explicit, immune to copy/style changes
        2. role         — matches how the accessibility tree (and users) see it
        3. aria-label    — explicit accessible name, no visible text needed
        4. css           — fine for structural/attribute selectors Playwright
                            doesn't have a semantic wrapper for
        5. xpath         — last resort; logged as a warning so it shows up in
                            code review / test output as a locator worth
                            replacing once a `data-testid` exists

    Page Objects call these directly (`Locators.test_id(self.page, "login-button")`)
    rather than embedding raw selector strings — the only thing that should
    ever change when the app's markup changes is this file's callers, not
    every test that happens to click that button.
    """

    @staticmethod
    def test_id(scope: LocatorScope, test_id: str) -> Locator:
        return scope.get_by_test_id(test_id)

    @staticmethod
    def role(
        scope: LocatorScope, role: str, *, name: str | None = None, exact: bool = False
    ) -> Locator:
        return scope.get_by_role(role, name=name, exact=exact)  # type: ignore[arg-type]

    @staticmethod
    def label(scope: LocatorScope, text: str, *, exact: bool = False) -> Locator:
        return scope.get_by_label(text, exact=exact)

    @staticmethod
    def css(scope: LocatorScope, selector: str) -> Locator:
        return scope.locator(selector)

    @staticmethod
    def text(scope: LocatorScope, text: str, *, exact: bool = False) -> Locator:
        """Visible-text lookup — for markup with no `data-testid`/role/label
        to key off, only rendered text (e.g. a Liferay-portal-style app
        driven by `getByText` in Playwright codegen).
        """
        return scope.get_by_text(text, exact=exact)

    @staticmethod
    def title(scope: LocatorScope, title: str, *, exact: bool = False) -> Locator:
        """`title`-attribute lookup (`getByTitle` in codegen) — distinct
        from `label()`'s `aria-label`/`<label>` lookup.
        """
        return scope.get_by_title(title, exact=exact)

    @staticmethod
    def link_with_text(scope: LocatorScope, text: str, *, exact: bool = False) -> Locator:
        """An `<a>` tag containing `text` — for links with no accessible
        role/name `get_by_role` can resolve, only a tag + visible text
        (`locator('a').filter(has_text=...)` in codegen). `exact=True` uses
        an anchored regex (`^text$`), matching codegen's own choice when it
        needs to disambiguate an otherwise-ambiguous substring match.
        """
        has_text = re.compile(f"^{re.escape(text)}$") if exact else text
        return Locators.css(scope, "a").filter(has_text=has_text)

    @staticmethod
    def xpath(scope: LocatorScope, expression: str) -> Locator:
        _logger.warning(
            f"xpath locator used: '{expression}' — last resort per locator strategy; "
            "prefer a data-testid/role/label selector once one is available"
        )
        return scope.locator(f"xpath={expression}")

    @staticmethod
    def resolve(
        scope: LocatorScope,
        *,
        test_id: str | None = None,
        role: str | None = None,
        role_name: str | None = None,
        label: str | None = None,
        css: str | None = None,
        xpath: str | None = None,
    ) -> Locator:
        """Pick the first strategy supplied, in priority order — for locator
        definitions that want a documented fallback chain in one place
        (e.g. a shared component used across pages with inconsistent
        markup) rather than a hardcoded single strategy.
        """
        if test_id is not None:
            return Locators.test_id(scope, test_id)
        if role is not None:
            return Locators.role(scope, role, name=role_name)
        if label is not None:
            return Locators.label(scope, label)
        if css is not None:
            return Locators.css(scope, css)
        if xpath is not None:
            return Locators.xpath(scope, xpath)
        raise ValueError("Locators.resolve() requires at least one strategy argument")
