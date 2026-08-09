"""Login-page detection — the missing check that let a login-page
redirect get reported as successful discovery of a customer's actual
target page (the second half of the validated bug this milestone fixes,
alongside `framework.extension.network_classification`).

Detection is evidence-based, same discipline as the rest of this
package: a page is only ever called a likely login page because of a
concrete, inspectable signal (its URL path, its title, or a
password-type input field among its discovered elements) — never a
guess, and `evidence` always lists which signals fired.
"""

from __future__ import annotations

from urllib.parse import urlparse

from framework.discovery.models import DiscoveredPage
from framework.extension.models import LoginPageSignal

_LOGIN_PATH_HINTS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/c/portal/login",
    "/auth/login",
    "/sso/login",
    "/logout",
)

_LOGIN_TITLE_HINTS: tuple[str, ...] = (
    "login",
    "log in",
    "sign in",
    "signin",
    "signed out",
    "logged out",
)


def detect_login_page(page: DiscoveredPage) -> LoginPageSignal:
    """A page is flagged as a likely login page when any one of its URL
    path, title, or a password-type input field matches a known signal —
    each signal alone is enough (a real login page reliably has at least
    one), and `evidence` records every signal that actually fired so a
    human reviewer can see why.
    """
    evidence: list[str] = []

    path_lower = urlparse(page.url).path.lower()
    if any(hint in path_lower for hint in _LOGIN_PATH_HINTS):
        evidence.append(f"URL path matches a known login pattern ({path_lower}).")

    title_lower = page.title.lower()
    if any(hint in title_lower for hint in _LOGIN_TITLE_HINTS):
        evidence.append(f"Page title suggests a login page ({page.title!r}).")

    has_password_field = any(
        element.attributes.get("type", "").lower() == "password" for element in page.elements
    )
    if has_password_field:
        evidence.append("A password-type input field was discovered on this page.")

    return LoginPageSignal(
        page_url=page.url,
        is_likely_login_page=bool(evidence),
        evidence=evidence,
    )


def detect_login_pages(pages: list[DiscoveredPage]) -> list[LoginPageSignal]:
    return [detect_login_page(page) for page in pages]
