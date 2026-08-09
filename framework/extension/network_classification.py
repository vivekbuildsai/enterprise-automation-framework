"""RAW -> NORMALIZE -> DEDUPLICATE -> CLASSIFY pipeline for discovered
network calls — the stage `framework.extension.correlation` was missing
before this milestone, which let CSS/JS/image/font requests and a
login-page redirect get treated as application-capability evidence (the
validated bug this module exists to fix: 81 raw network calls on a real
customer page, only a handful of which were genuine application API
traffic).

Classification is a most-specific-first rule chain over data the discovery
engine already captured (`method`, `path`, `host`, body-key shapes) — never
a guess, and never based on a value that could carry a secret. Every count
in the returned `NetworkClassificationSummary` is a real `len()` over the
actual input/output lists (see that model's docstring) — nothing here
invents or estimates a number.
"""

from __future__ import annotations

from urllib.parse import urlparse

from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.models import (
    ClassifiedNetworkCall,
    NetworkCallClassification,
    NetworkClassificationResult,
    NetworkClassificationSummary,
)

_AUTH_PATH_HINTS: tuple[str, ...] = (
    "/login",
    "/signin",
    "/sign-in",
    "/c/portal/login",
    "/auth/",
    "/authenticate",
    "/sso/",
    "/oauth",
    "/logout",
)

_FRAMEWORK_ASSET_HINTS: tuple[str, ...] = (
    "jquery",
    "bootstrap",
    "modernizr",
    "polyfill",
    "webpack",
    "react",
    "angular",
    "vue.js",
    "barebone",
)

_STATIC_ASSET_EXTENSIONS: tuple[str, ...] = (
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".map",
    ".mp4",
    ".webm",
)

_STATIC_ASSET_PATH_HINTS: tuple[str, ...] = (
    "/combo/",
    "/html/css/",
    "/html/js/",
    "/html/themes/",
    "/static/",
    "/assets/",
    "/fonts/",
    "/images/",
    "/img/",
    "/favicon",
)

_DOCUMENT_EXTENSIONS: tuple[str, ...] = (".pdf", ".doc", ".docx", ".xls", ".xlsx")

_ANALYTICS_HOST_HINTS: tuple[str, ...] = (
    "google-analytics.com",
    "googletagmanager.com",
    "segment.io",
    "segment.com",
    "mixpanel.com",
    "hotjar.com",
    "doubleclick.net",
    "fullstory.com",
    "amplitude.com",
    "clarity.ms",
)


def _classify_same_origin(
    call: DiscoveredNetworkCall, *, path_lower: str
) -> tuple[NetworkCallClassification, str]:
    has_body_shape = bool(call.request_body_keys or call.response_body_keys)
    looks_like_static_by_extension = "." in path_lower.rsplit("/", 1)[
        -1
    ] and not path_lower.endswith((".json", ".do", ".action"))
    if has_body_shape or not looks_like_static_by_extension:
        return (
            NetworkCallClassification.APPLICATION_API,
            "Same-origin call with an application-shaped path or JSON body.",
        )
    return NetworkCallClassification.UNKNOWN, "No classification rule matched with confidence."


def _classify_one(
    call: DiscoveredNetworkCall, *, page_host: str
) -> tuple[NetworkCallClassification, str]:
    """A single-return elif chain (not early returns) — deliberately, so
    the rule-chain precedence stays obviously most-specific-first in one
    place without tripping a "too many returns" complexity warning.
    """
    path_lower = call.path.lower()
    host_lower = call.host.lower()

    if any(hint in path_lower for hint in _AUTH_PATH_HINTS):
        classification = NetworkCallClassification.AUTHENTICATION
        reason = f"Path matches an authentication pattern ({call.path})."
    elif any(hint in path_lower for hint in _FRAMEWORK_ASSET_HINTS):
        classification = NetworkCallClassification.FRAMEWORK_ASSET
        reason = f"Path references a known front-end library/bundler ({call.path})."
    elif path_lower.endswith(_STATIC_ASSET_EXTENSIONS) or any(
        hint in path_lower for hint in _STATIC_ASSET_PATH_HINTS
    ):
        classification = NetworkCallClassification.STATIC_ASSET
        reason = f"Path is a static asset ({call.path})."
    elif path_lower.endswith(_DOCUMENT_EXTENSIONS):
        classification = NetworkCallClassification.DOCUMENT
        reason = f"Path is a document download ({call.path})."
    elif host_lower and any(hint in host_lower for hint in _ANALYTICS_HOST_HINTS):
        classification = NetworkCallClassification.ANALYTICS
        reason = f"Host is a known analytics/tracking domain ({call.host})."
    elif host_lower and page_host and host_lower != page_host.lower():
        classification = NetworkCallClassification.THIRD_PARTY
        reason = f"Host ({call.host}) differs from the discovered page's own host ({page_host})."
    else:
        classification, reason = _classify_same_origin(call, path_lower=path_lower)

    return classification, reason


def _dedup_key(
    call: DiscoveredNetworkCall,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        call.method.upper(),
        call.path,
        tuple(sorted(call.query_param_names)),
        tuple(sorted(call.request_body_keys)),
        tuple(sorted(call.response_body_keys)),
    )


def classify_network_calls(
    calls: list[DiscoveredNetworkCall], *, page_host: str = ""
) -> NetworkClassificationResult:
    """Normalizes + deduplicates + classifies `calls`. `page_host` is the
    discovered page's own hostname (e.g. `urlparse(page.url).netloc`),
    used to tell same-origin application traffic apart from third-party
    traffic — pass `""` when unknown, which degrades `THIRD_PARTY`
    detection but never crashes.
    """
    deduped: dict[
        tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], DiscoveredNetworkCall
    ] = {}
    duplicate_counts: dict[
        tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], int
    ] = {}
    for call in calls:
        key = _dedup_key(call)
        duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
        deduped.setdefault(key, call)

    classified_calls: list[ClassifiedNetworkCall] = []
    summary = NetworkClassificationSummary(raw_count=len(calls))
    summary.duplicates_removed = len(calls) - len(deduped)

    for key, call in deduped.items():
        classification, reason = _classify_one(call, page_host=page_host)
        classified_calls.append(
            ClassifiedNetworkCall(
                call=call,
                classification=classification,
                reason=reason,
                duplicate_count=duplicate_counts[key],
            )
        )
        if classification in (
            NetworkCallClassification.STATIC_ASSET,
            NetworkCallClassification.FRAMEWORK_ASSET,
        ):
            summary.static_or_framework_ignored += 1
        elif classification == NetworkCallClassification.ANALYTICS:
            summary.analytics_ignored += 1
        elif classification == NetworkCallClassification.THIRD_PARTY:
            summary.third_party_ignored += 1
        elif classification == NetworkCallClassification.DOCUMENT:
            summary.document_ignored += 1
        elif classification == NetworkCallClassification.AUTHENTICATION:
            summary.authentication_count += 1
        elif classification == NetworkCallClassification.APPLICATION_API:
            summary.application_candidate_count += 1
        else:
            summary.unknown_count += 1

    return NetworkClassificationResult(
        raw_calls=list(calls),
        classified_calls=classified_calls,
        summary=summary,
    )


def page_host_from_url(url: str) -> str:
    """Small shared helper so callers never have to remember the
    `urlparse(...).netloc` incantation themselves — same convenience
    precedent as the rest of this package's thin helper functions.
    """
    return urlparse(url).netloc
