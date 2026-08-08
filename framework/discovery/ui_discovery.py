from __future__ import annotations

from urllib.parse import urlparse

from playwright.sync_api import ElementHandle, Page

from framework.discovery.models import DiscoveredElement, DiscoveredLocator, DiscoveredPage
from framework.logger import get_logger

_logger = get_logger("UIDiscoveryEngine")

_INTERACTIVE_SELECTOR = (
    "button, a[href], input, select, textarea, "
    "[role=button], [role=link], [role=checkbox], [role=radio], [role=combobox]"
)

_IMPLICIT_ROLES = {
    "a": "link",
    "button": "button",
    "select": "combobox",
    "textarea": "textbox",
    "input": "textbox",
}


class UIDiscoveryEngine:
    """Passive, read-only UI discovery. Inspects the DOM of a page the
    caller is already authorized to access (an already-authenticated
    `Page`, or a public/staging URL) and extracts interactive elements
    with the best available locator, using the same
    testid > role > label > css priority `framework.locators.Locators`
    already encodes for hand-written Page Objects.

    Never submits a form, never attempts login/credential guessing, never
    performs a destructive action — discovery is look-don't-touch. Only
    run this against an application you are authorized to test.

    An element with no genuinely stable locator (no test id, no role +
    accessible name, no id/name attribute) is dropped rather than emitted
    with a guessed `nth-child`/xpath-position selector — the same
    "never invent a locator" rule the rest of this framework follows.
    """

    def __init__(self, page: Page) -> None:
        self._page = page

    def discover_page(self, url: str | None = None) -> DiscoveredPage:
        if url:
            self._page.goto(url)
        self._page.wait_for_load_state("domcontentloaded")

        elements: list[DiscoveredElement] = []
        for handle in self._page.query_selector_all(_INTERACTIVE_SELECTOR):
            element = self._describe(handle)
            if element is not None:
                elements.append(element)

        page = DiscoveredPage(url=self._page.url, title=self._page.title(), elements=elements)
        _logger.info(f"Discovered {len(elements)} interactive elements on {page.url}")
        return page

    def crawl(self, start_url: str, *, max_pages: int = 5) -> list[DiscoveredPage]:
        """Small, bounded, same-origin breadth-first crawl — not a
        general-purpose spider. Stops at `max_pages`. Only run this
        against an application you are authorized to test; it follows
        every same-origin link it finds, so point it at a scoped
        staging/test environment, not a shared production system.
        """
        origin = urlparse(start_url).netloc
        visited: set[str] = set()
        queue = [start_url]
        pages: list[DiscoveredPage] = []

        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            page = self.discover_page(url)
            pages.append(page)
            if len(pages) >= max_pages:
                break

            hrefs = self._page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for href in hrefs:
                if urlparse(href).netloc == origin and href not in visited:
                    queue.append(href)

        return pages

    def _describe(self, handle: ElementHandle) -> DiscoveredElement | None:
        tag: str = handle.evaluate("el => el.tagName.toLowerCase()")
        test_id = handle.get_attribute("data-testid") or handle.get_attribute("data-test-id")
        role = handle.get_attribute("role") or _IMPLICIT_ROLES.get(tag)
        aria_label = handle.get_attribute("aria-label")
        text = (handle.inner_text() or "").strip()[:120]
        element_id = handle.get_attribute("id")
        name_attr = handle.get_attribute("name")
        label_text = self._associated_label_text(handle)

        # Visible text is only a genuine accessible name for buttons/links —
        # real ARIA default-name computation. For form controls (select,
        # textarea, ...) inner_text() can pick up unrelated child content
        # (e.g. a <select>'s <option> text), which is not the element's own
        # name, so only aria-label counts there.
        text_counts_as_name = tag in ("button", "a") or role in ("button", "link")
        accessible_name = aria_label or (text if text_counts_as_name else None) or None

        locator = self._best_locator(
            tag=tag,
            test_id=test_id,
            role=role,
            accessible_name=accessible_name,
            label_text=label_text,
            element_id=element_id,
            name_attr=name_attr,
        )
        if locator is None:
            return None

        attributes = {
            attr: value
            for attr in ("type", "href", "placeholder")
            if (value := handle.get_attribute(attr))
        }
        return DiscoveredElement(
            tag=tag, element_type=role or tag, text=text, locator=locator, attributes=attributes
        )

    @staticmethod
    def _associated_label_text(handle: ElementHandle) -> str | None:
        """A `<label for="...">` pointing at this element's `id` — a
        genuinely stable, human-meaningful locator source
        (`Locators.label()` -> Playwright's `get_by_label()`), ranked
        above a bare CSS id selector in `_best_locator`.
        """
        text: str | None = handle.evaluate(
            """el => {
                if (!el.id) return null;
                const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                return label ? label.textContent.trim() : null;
            }"""
        )
        return text or None

    @staticmethod
    def _best_locator(
        *,
        tag: str,
        test_id: str | None,
        role: str | None,
        accessible_name: str | None,
        label_text: str | None,
        element_id: str | None,
        name_attr: str | None,
    ) -> DiscoveredLocator | None:
        if test_id:
            return DiscoveredLocator(strategy="test_id", value=test_id)
        if role and accessible_name:
            return DiscoveredLocator(
                strategy="role", value=role, role=role, accessible_name=accessible_name
            )
        if label_text:
            return DiscoveredLocator(strategy="label", value=label_text)
        if element_id:
            return DiscoveredLocator(strategy="css", value=f"#{element_id}")
        if name_attr:
            return DiscoveredLocator(strategy="css", value=f'{tag}[name="{name_attr}"]')
        return None
