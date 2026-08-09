from __future__ import annotations

import json
from typing import Any, TypedDict
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page

from framework.discovery.models import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredNetworkCall,
    DiscoveredPage,
)
from framework.logger import get_logger
from framework.network.interceptor import CapturedExchange, NetworkInterceptor

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

# Reads every attribute `_describe` needs, for every matched element, in one
# browser-side pass — replaces what used to be ~9 separate Playwright IPC
# round trips *per element* (evaluate/get_attribute/inner_text calls) with
# exactly one round trip for the whole page. Only raw DOM data crosses the
# JS/Python boundary here; the locator-priority *decision* (`_best_locator`)
# stays pure Python, unchanged, so this never re-implements framework
# semantics in JavaScript — it only relocates where the same raw facts are
# read from.
_EXTRACT_ELEMENTS_JS = """
els => els.map(el => {
    const tag = el.tagName.toLowerCase();
    let labelText = null;
    if (el.id) {
        const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        labelText = label ? label.textContent.trim() : null;
    }
    return {
        tag,
        testId: el.getAttribute('data-testid') || el.getAttribute('data-test-id'),
        role: el.getAttribute('role'),
        ariaLabel: el.getAttribute('aria-label'),
        text: (el.innerText || '').trim().slice(0, 120),
        elementId: el.id || null,
        nameAttr: el.getAttribute('name'),
        labelText,
        type: el.getAttribute('type'),
        href: el.getAttribute('href'),
        placeholder: el.getAttribute('placeholder'),
    };
})
"""


def _json_shape(value: Any, *, _prefix: str = "") -> list[str]:
    """Recursively collects JSON key *names* only, as dotted paths for
    nested objects — never a value. A JSON array is walked via its first
    element only (array items normally share one shape); a scalar, empty
    list, or `None` contributes nothing further. This is the "shape, never
    the value" rule `DiscoveredNetworkCall` depends on to stay safe to
    persist even when the real body carried PII or secrets.
    """
    if isinstance(value, dict):
        keys: list[str] = []
        for key, nested in value.items():
            path = f"{_prefix}.{key}" if _prefix else key
            keys.append(path)
            keys.extend(_json_shape(nested, _prefix=path))
        return keys
    if isinstance(value, list) and value:
        return _json_shape(value[0], _prefix=_prefix)
    return []


def _to_discovered_network_call(exchange: CapturedExchange) -> DiscoveredNetworkCall:
    parsed = urlparse(exchange.url)
    request_body_keys: list[str] = []
    if exchange.request_body:
        try:
            request_body_keys = _json_shape(json.loads(exchange.request_body))
        except (ValueError, TypeError):
            request_body_keys = []
    return DiscoveredNetworkCall(
        method=exchange.method,
        path=parsed.path,
        status=exchange.status,
        host=parsed.netloc,
        query_param_names=sorted(parse_qs(parsed.query).keys()),
        request_body_keys=request_body_keys,
        response_body_keys=_json_shape(exchange.response_json),
    )


class _RawElement(TypedDict):
    tag: str
    testId: str | None
    role: str | None
    ariaLabel: str | None
    text: str
    elementId: str | None
    nameAttr: str | None
    labelText: str | None
    type: str | None
    href: str | None
    placeholder: str | None


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

    Network activity capture is opt-in (`capture_network=True`) and off by
    default, so existing DOM-only callers see no behavior change. When
    enabled, captured exchanges are recorded as shape-only
    `DiscoveredNetworkCall`s — method, path, status, and key *names* only,
    never request/response values — so a discovery report stays safe to
    persist even against an authenticated session carrying real data.
    """

    def __init__(self, page: Page) -> None:
        self._page = page

    def discover_page(
        self,
        url: str | None = None,
        *,
        capture_network: bool = False,
        network_url_pattern: str = "**/*",
    ) -> DiscoveredPage:
        """`capture_network=False` (the default) preserves the original
        DOM-only behavior exactly — no listener is attached, so existing
        callers see zero change. Opting in reuses `NetworkInterceptor`
        (the same capture mechanism the UI-vs-database validation pipeline
        already relies on) rather than re-implementing response capture;
        exchanges are converted to shape-only `DiscoveredNetworkCall`s (see
        `_to_discovered_network_call`) before ever reaching the report.
        """
        if not capture_network:
            if url:
                self._page.goto(url)
            self._page.wait_for_load_state("domcontentloaded")
            return self._extract_page(network_calls=[])

        with NetworkInterceptor(self._page, url_pattern=network_url_pattern) as interceptor:
            if url:
                self._page.goto(url)
            self._page.wait_for_load_state("domcontentloaded")
            self._page.wait_for_load_state("networkidle")
        network_calls = [_to_discovered_network_call(e) for e in interceptor.captured]
        return self._extract_page(network_calls=network_calls)

    def _extract_page(self, *, network_calls: list[DiscoveredNetworkCall]) -> DiscoveredPage:
        raw_elements: list[_RawElement] = self._page.eval_on_selector_all(
            _INTERACTIVE_SELECTOR, _EXTRACT_ELEMENTS_JS
        )
        elements = [
            described for raw in raw_elements if (described := self._describe(raw)) is not None
        ]

        page = DiscoveredPage(
            url=self._page.url,
            title=self._page.title(),
            elements=elements,
            network_calls=network_calls,
        )
        _logger.info(
            f"Discovered {len(elements)} interactive elements and "
            f"{len(network_calls)} network call(s) on {page.url}"
        )
        return page

    def crawl(
        self,
        start_url: str,
        *,
        max_pages: int = 5,
        capture_network: bool = False,
        network_url_pattern: str = "**/*",
    ) -> list[DiscoveredPage]:
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

            page = self.discover_page(
                url, capture_network=capture_network, network_url_pattern=network_url_pattern
            )
            pages.append(page)
            if len(pages) >= max_pages:
                break

            hrefs = self._page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for href in hrefs:
                if urlparse(href).netloc == origin and href not in visited:
                    queue.append(href)

        return pages

    def _describe(self, raw: _RawElement) -> DiscoveredElement | None:
        tag = raw["tag"]
        test_id = raw["testId"]
        role = raw["role"] or _IMPLICIT_ROLES.get(tag)
        aria_label = raw["ariaLabel"]
        text = raw["text"]
        element_id = raw["elementId"]
        name_attr = raw["nameAttr"]
        label_text = raw["labelText"]

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

        attributes: dict[str, Any] = {
            attr: value for attr in ("type", "href", "placeholder") if (value := raw.get(attr))
        }
        return DiscoveredElement(
            tag=tag, element_type=role or tag, text=text, locator=locator, attributes=attributes
        )

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
