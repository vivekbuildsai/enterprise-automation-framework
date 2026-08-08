"""UI/API/database correlation — takes what `UIDiscoveryEngine` observed a
new, zero-test UI actually calling (`DiscoveredNetworkCall`s) and matches
it against the existing framework's `CapabilityCatalog`
(`framework.sync.capability_catalog`), the same "Existing API capability /
New UI dependency / Relationship / Evidence" comparison the governing
worked example describes.

Every match records the concrete evidence behind it — never a bare label.
A single weak signal (endpoint pattern alone, with a different HTTP
method) is deliberately downgraded to `POSSIBLY_REUSABLE`, and multiple
equally-good matches yield `MANUAL_REVIEW` rather than an arbitrary pick —
this module never *decides* for the customer, it only surfaces the
comparison for a human to review (see docs/FrameworkSync.md, "Existing
framework as a product asset").
"""

from __future__ import annotations

import re
from functools import cache

from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.models import RelationshipStatus, UIAPICorrelation
from framework.sync.models import CapabilityCatalog, CapabilityCategory, ExistingCapability


@cache
def _pattern_regex(endpoint_pattern: str) -> re.Pattern[str]:
    """The exact counterpart to `framework.sync.capability_catalog._normalize_path`,
    which is what produced the `{param}` placeholder in the first place —
    turns it back into a `[^/]+` regex segment so a concrete discovered
    path (`/employees/42`) can be matched against the capability's pattern
    (`/employees/{param}`). Cached per distinct pattern string: correlating
    N discovered calls against M catalog capabilities recompiles the same
    handful of patterns up to N*M times without this — a real, measured
    regression on a customer-scale catalog (same class of fix as
    `framework.sync.detectors`'s `@lru_cache`, see docs/FrameworkSync.md
    "Performance").
    """
    escaped = re.escape(endpoint_pattern).replace(r"\{param\}", r"[^/]+")
    return re.compile(f"^{escaped}$")


def _endpoint_matches(capability: ExistingCapability, path: str) -> bool:
    if capability.endpoint_pattern is None:
        return False
    return _pattern_regex(capability.endpoint_pattern).match(path) is not None


def _table_name_candidates(path: str) -> set[str]:
    """Literal (non-numeric) path segments, plus a naively singularized
    (`strip trailing 's'`) variant of each — e.g. `/employees/42` yields
    `{"employees", "employee"}`. Deliberately simple: an over-generous
    candidate set here only widens what *might* match, never fabricates a
    match by itself — a real match still requires equality against an
    actual `table:<name>` capability the customer's own code references.
    """
    candidates: set[str] = set()
    for segment in path.strip("/").split("/"):
        if not segment or segment.isdigit():
            continue
        candidates.add(segment)
        if segment.endswith("s") and len(segment) > 1:
            candidates.add(segment[:-1])
    return candidates


def correlate_network_call(
    call: DiscoveredNetworkCall, catalog: CapabilityCatalog
) -> UIAPICorrelation:
    """Matches one discovered network call against the existing API
    capability catalog by (endpoint pattern, HTTP method) — the same two
    signals the governing worked example uses ("endpoint match, HTTP
    method match"). `LIKELY_REUSABLE` requires both signals to agree on
    exactly one capability; a pattern-only match is downgraded to
    `POSSIBLY_REUSABLE`; two or more equally-good matches yield
    `MANUAL_REVIEW` rather than an arbitrary pick.
    """
    api_capabilities = [
        c for c in catalog.capabilities if c.category == CapabilityCategory.API_CLIENT
    ]

    exact_matches = [
        c
        for c in api_capabilities
        if c.http_method == call.method and _endpoint_matches(c, call.path)
    ]
    if len(exact_matches) == 1:
        capability = exact_matches[0]
        evidence = ["endpoint pattern match", "HTTP method match"]
        if capability.endpoint_pattern == call.path:
            evidence.append("exact literal path match")
        return UIAPICorrelation(
            discovered_call=call,
            matched_capability=capability,
            status=RelationshipStatus.LIKELY_REUSABLE,
            evidence=evidence,
        )
    if len(exact_matches) > 1:
        return UIAPICorrelation(
            discovered_call=call,
            status=RelationshipStatus.MANUAL_REVIEW,
            evidence=[
                f"{len(exact_matches)} existing API capabilities match both endpoint "
                "pattern and HTTP method — ambiguous, needs human review"
            ],
        )

    path_only_matches = [c for c in api_capabilities if _endpoint_matches(c, call.path)]
    if len(path_only_matches) == 1:
        capability = path_only_matches[0]
        return UIAPICorrelation(
            discovered_call=call,
            matched_capability=capability,
            status=RelationshipStatus.POSSIBLY_REUSABLE,
            evidence=[
                "endpoint pattern match",
                f"HTTP method differs (existing={capability.http_method}, new UI={call.method})",
            ],
        )
    if len(path_only_matches) > 1:
        return UIAPICorrelation(
            discovered_call=call,
            status=RelationshipStatus.MANUAL_REVIEW,
            evidence=[
                f"{len(path_only_matches)} existing API capabilities match the endpoint "
                "pattern but not the HTTP method — ambiguous, needs human review"
            ],
        )

    return UIAPICorrelation(
        discovered_call=call,
        status=RelationshipStatus.NOT_FOUND,
        evidence=["no existing API capability matches this endpoint"],
    )


def correlate_network_calls(
    calls: list[DiscoveredNetworkCall], catalog: CapabilityCatalog
) -> list[UIAPICorrelation]:
    return [correlate_network_call(call, catalog) for call in calls]


def correlate_database_usage(
    calls: list[DiscoveredNetworkCall], catalog: CapabilityCatalog
) -> list[UIAPICorrelation]:
    """Compares each discovered call's literal path segments against known
    `table:<name>` capabilities (see `framework.sync.capability_catalog`).
    A path segment matching a real table name is real, inspectable
    evidence that a discovered UI dependency's data ultimately reaches
    that table — never a guess at column-level shape, since a network
    call's JSON keys are application-level field names, not a database
    schema.
    """
    table_capabilities: dict[str, ExistingCapability] = {}
    for capability in catalog.capabilities:
        if (
            capability.category == CapabilityCategory.DATABASE_UTILITY
            and capability.name.startswith("table:")
        ):
            table_capabilities[capability.name.removeprefix("table:")] = capability

    correlations: list[UIAPICorrelation] = []
    for call in calls:
        matches = [
            table_capabilities[name]
            for name in sorted(_table_name_candidates(call.path))
            if name in table_capabilities
        ]
        if len(matches) == 1:
            correlations.append(
                UIAPICorrelation(
                    discovered_call=call,
                    matched_capability=matches[0],
                    status=RelationshipStatus.POSSIBLY_REUSABLE,
                    evidence=[f"path segment matches known table '{matches[0].name}'"],
                )
            )
        elif len(matches) > 1:
            correlations.append(
                UIAPICorrelation(
                    discovered_call=call,
                    status=RelationshipStatus.MANUAL_REVIEW,
                    evidence=[f"{len(matches)} known tables match path segments — ambiguous"],
                )
            )
        else:
            correlations.append(
                UIAPICorrelation(
                    discovered_call=call,
                    status=RelationshipStatus.NOT_FOUND,
                    evidence=["no known database table matches this path"],
                )
            )
    return correlations
