"""Extension gap analysis + test opportunity inventory — the two
customer-facing artifacts built on top of `framework.extension.correlation`:
the "EXISTING FRAMEWORK EXTENSION REPORT" (REUSE_EXISTING / EXTEND_EXISTING
/ CREATE_NEW / UNKNOWN / MANUAL_REVIEW per discovered subject) and a "Test
Opportunity Inventory" (named, human-reviewable testing opportunities —
never auto-generated test cases; see the "Test case generation boundary"
requirement in docs/FrameworkSync.md).

Every classification here is deterministic and evidence-based; no AI
involved (see `framework.extension.ai_recommendations` for the optional
AI-assisted layer that only ever fires on `MANUAL_REVIEW`/`UNKNOWN`
items).
"""

from __future__ import annotations

from framework.discovery.models import DiscoveredPage
from framework.extension.correlation import correlate_database_usage, correlate_network_calls
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionSubjectType,
    RelationshipStatus,
    TestOpportunity,
    UIAPICorrelation,
)
from framework.sync.models import CapabilityCatalog, CapabilityCategory

_STATUS_TO_CLASSIFICATION: dict[RelationshipStatus, ExtensionClassification] = {
    RelationshipStatus.LIKELY_REUSABLE: ExtensionClassification.REUSE_EXISTING,
    RelationshipStatus.POSSIBLY_REUSABLE: ExtensionClassification.EXTEND_EXISTING,
    RelationshipStatus.NOT_FOUND: ExtensionClassification.CREATE_NEW,
    RelationshipStatus.MANUAL_REVIEW: ExtensionClassification.MANUAL_REVIEW,
}

# Confidence for `ExtensionItem`s built without an underlying
# `UIAPICorrelation` (a page, the aggregate authentication item, a
# shared-infrastructure item) — reflects how confident the classification
# itself is, not a match strength. `REUSE_EXISTING` here comes from a
# single title/category signal (weaker than a correlation's endpoint+method
# match), so it is scored below `correlation._CONFIDENCE_PATTERN_AND_METHOD_MATCH`.
_CONFIDENCE_TITLE_MATCH = 65
_CONFIDENCE_SHARED_CAPABILITY_PRESENT = 75
_CONFIDENCE_CONFIDENT_CREATE_NEW = 85
_CONFIDENCE_NO_DATA_TO_EVALUATE = 20
_CONFIDENCE_MANUAL_REVIEW = 30


def _confidence_for_classification(classification: ExtensionClassification) -> int:
    """The default confidence for an `ExtensionItem` with no underlying
    correlation to copy a score from — callers that have stronger,
    signal-specific evidence (e.g. `_page_extension_item`'s title match)
    pass their own value instead of relying on this fallback.
    """
    if classification == ExtensionClassification.CREATE_NEW:
        return _CONFIDENCE_CONFIDENT_CREATE_NEW
    if classification == ExtensionClassification.MANUAL_REVIEW:
        return _CONFIDENCE_MANUAL_REVIEW
    if classification == ExtensionClassification.UNKNOWN:
        return _CONFIDENCE_NO_DATA_TO_EVALUATE
    return _CONFIDENCE_SHARED_CAPABILITY_PRESENT


def _correlation_reason(correlation: UIAPICorrelation) -> str:
    call = correlation.discovered_call
    capability = correlation.matched_capability
    if correlation.status == RelationshipStatus.LIKELY_REUSABLE and capability is not None:
        return f"{call.method} {call.path} matches existing capability '{capability.name}'."
    if correlation.status == RelationshipStatus.POSSIBLY_REUSABLE and capability is not None:
        return (
            f"{call.method} {call.path} partially matches existing capability "
            f"'{capability.name}' — likely needs adaptation."
        )
    if correlation.status == RelationshipStatus.MANUAL_REVIEW:
        return f"{call.method} {call.path} matched more than one existing capability equally well."
    return f"{call.method} {call.path} has no matching existing capability."


def _page_extension_item(page: DiscoveredPage, catalog: CapabilityCatalog) -> ExtensionItem:
    """A newly discovered page has, by definition, zero existing
    automation on it — the only way it becomes `REUSE_EXISTING` is if an
    existing Page Object's/component's *name* already contains this
    page's title, real evidence the same screen is already automated
    elsewhere (the "multiple existing UIs share one screen" scenario).
    Anything short of that stays `CREATE_NEW` — never guessed.
    """
    normalized_title = page.title.strip().lower().replace(" ", "")
    if normalized_title:
        for capability in catalog.capabilities:
            if capability.category not in (
                CapabilityCategory.PAGE_OBJECT,
                CapabilityCategory.COMPONENT,
            ):
                continue
            if normalized_title in capability.name.lower():
                return ExtensionItem(
                    subject=page.title or page.url,
                    subject_type=ExtensionSubjectType.UI_PAGE,
                    classification=ExtensionClassification.REUSE_EXISTING,
                    matched_capability=capability,
                    reason=(
                        f"An existing Page Object/component named '{capability.name}' "
                        "matches this page's title."
                    ),
                    evidence=[
                        f"page title '{page.title}' found in capability name '{capability.name}'"
                    ],
                    confidence=_CONFIDENCE_TITLE_MATCH,
                )
    return ExtensionItem(
        subject=page.title or page.url,
        subject_type=ExtensionSubjectType.UI_PAGE,
        classification=ExtensionClassification.CREATE_NEW,
        reason="No existing Page Object or component matches this newly discovered page.",
        evidence=["new UI page has no automation today"],
        confidence=_confidence_for_classification(ExtensionClassification.CREATE_NEW),
    )


def _authentication_extension_item(catalog: CapabilityCatalog) -> ExtensionItem:
    auth_capabilities = [
        c for c in catalog.capabilities if c.category == CapabilityCategory.AUTHENTICATION
    ]
    if not auth_capabilities:
        return ExtensionItem(
            subject="Authentication",
            subject_type=ExtensionSubjectType.AUTHENTICATION,
            classification=ExtensionClassification.UNKNOWN,
            reason="No existing authentication mechanism was detected to compare against.",
            confidence=_confidence_for_classification(ExtensionClassification.UNKNOWN),
        )
    capability = auth_capabilities[0]
    return ExtensionItem(
        subject="Authentication",
        subject_type=ExtensionSubjectType.AUTHENTICATION,
        classification=ExtensionClassification.REUSE_EXISTING,
        matched_capability=capability,
        reason=(
            f"The existing framework already has a detected authentication mechanism "
            f"({capability.name}); a new UI on the same backend is expected to reuse it "
            "rather than implement a second one."
        ),
        evidence=[capability.evidence] if capability.evidence else [],
        confidence=_confidence_for_classification(ExtensionClassification.REUSE_EXISTING),
    )


def _shared_capability_item(
    catalog: CapabilityCatalog,
    *,
    category: CapabilityCategory,
    subject: str,
    subject_type: ExtensionSubjectType,
    absent_reason: str,
) -> ExtensionItem:
    """Report shared framework infrastructure separately from page/API
    correlation.  Presence only supports a reusable *candidate*, not a
    claim that a new UI already uses it; the evidence records exactly where
    the customer can inspect the detected asset.
    """
    capabilities = [c for c in catalog.capabilities if c.category == category]
    if not capabilities:
        return ExtensionItem(
            subject=subject,
            subject_type=subject_type,
            classification=ExtensionClassification.UNKNOWN,
            reason=absent_reason,
            confidence=_confidence_for_classification(ExtensionClassification.UNKNOWN),
        )
    capability = capabilities[0]
    return ExtensionItem(
        subject=subject,
        subject_type=subject_type,
        classification=ExtensionClassification.REUSE_EXISTING,
        matched_capability=capability,
        reason=(
            f"Existing {subject.lower()} capability '{capability.name}' was detected; "
            "reuse it unless the new UI needs behavior not covered by this asset."
        ),
        evidence=(
            [capability.evidence, capability.source_file]
            if capability.evidence or capability.source_file
            else []
        ),
        confidence=_confidence_for_classification(ExtensionClassification.REUSE_EXISTING),
    )


def build_extension_items(
    pages: list[DiscoveredPage], catalog: CapabilityCatalog
) -> list[ExtensionItem]:
    """The "EXISTING FRAMEWORK EXTENSION REPORT" body — one `ExtensionItem`
    per discovered page, per discovered network call, and per
    database-table correlation that actually found something, plus one
    aggregate authentication item. Pages with no discovered network calls
    contribute a UI-only item and nothing else — this never fabricates API
    or database rows a page didn't actually generate.
    """
    items: list[ExtensionItem] = [_page_extension_item(page, catalog) for page in pages]

    all_calls = [call for page in pages for call in page.network_calls]
    if all_calls:
        for correlation in correlate_network_calls(all_calls, catalog):
            call = correlation.discovered_call
            items.append(
                ExtensionItem(
                    subject=f"{call.method} {call.path}",
                    subject_type=ExtensionSubjectType.API_ENDPOINT,
                    classification=_STATUS_TO_CLASSIFICATION[correlation.status],
                    matched_capability=correlation.matched_capability,
                    reason=_correlation_reason(correlation),
                    evidence=correlation.evidence,
                    confidence=correlation.confidence,
                )
            )
        for correlation in correlate_database_usage(all_calls, catalog):
            if correlation.status == RelationshipStatus.NOT_FOUND:
                continue  # not every API call touches a known table — silence isn't a gap
            call = correlation.discovered_call
            items.append(
                ExtensionItem(
                    subject=f"Data behind {call.method} {call.path}",
                    subject_type=ExtensionSubjectType.DATABASE,
                    classification=_STATUS_TO_CLASSIFICATION[correlation.status],
                    matched_capability=correlation.matched_capability,
                    reason=_correlation_reason(correlation),
                    evidence=correlation.evidence,
                )
            )

    items.append(_authentication_extension_item(catalog))
    items.extend(
        [
            _shared_capability_item(
                catalog,
                category=CapabilityCategory.DATABASE_UTILITY,
                subject="Database infrastructure",
                subject_type=ExtensionSubjectType.DATABASE,
                absent_reason="No existing database utility was detected to compare against.",
            ),
            _shared_capability_item(
                catalog,
                category=CapabilityCategory.VALIDATION,
                subject="Validation",
                subject_type=ExtensionSubjectType.VALIDATION,
                absent_reason="No existing validation capability was detected to compare against.",
            ),
            _shared_capability_item(
                catalog,
                category=CapabilityCategory.TEST_DATA,
                subject="Test data",
                subject_type=ExtensionSubjectType.TEST_DATA,
                absent_reason="No existing test-data capability was detected to compare against.",
            ),
            _shared_capability_item(
                catalog,
                category=CapabilityCategory.REPORTING,
                subject="Reporting",
                subject_type=ExtensionSubjectType.REPORTING,
                absent_reason="No existing reporting capability was detected to compare against.",
            ),
        ]
    )
    return items


def build_test_opportunities(
    pages: list[DiscoveredPage], catalog: CapabilityCatalog | None = None
) -> list[TestOpportunity]:
    """One `TestOpportunity` per discovered page — a named, human-reviewable
    unit worth testing, never a generated test case (see the "Test case
    generation boundary" requirement in docs/FrameworkSync.md).
    `suggested_scenario_types` are deterministic, evidence-based advisory
    labels only: `validation` only when the page actually has input-like
    elements, `ui_api_consistency` only when the page actually made a
    network call during discovery, and `ui_api_db_consistency` only when
    `catalog` is supplied and at least one of those calls correlates to a
    known database table — never invented for a page with no such
    evidence.
    """
    opportunities: list[TestOpportunity] = []
    for page in pages:
        related_elements = [f"{el.locator.strategy}:{el.locator.value}" for el in page.elements]
        related_api_paths = sorted({call.path for call in page.network_calls})

        scenario_types = ["happy_path"]
        if any(el.tag in ("input", "select", "textarea") for el in page.elements):
            scenario_types.append("validation")
        if related_api_paths:
            scenario_types.append("ui_api_consistency")
        if catalog is not None and page.network_calls:
            db_correlations = correlate_database_usage(page.network_calls, catalog)
            if any(c.status != RelationshipStatus.NOT_FOUND for c in db_correlations):
                scenario_types.append("ui_api_db_consistency")

        opportunities.append(
            TestOpportunity(
                name=page.title or page.url,
                page_url=page.url,
                related_elements=related_elements,
                related_api_paths=related_api_paths,
                suggested_scenario_types=scenario_types,
            )
        )
    return opportunities


def format_reuse_matrix(items: list[ExtensionItem]) -> str:
    """Renders the human-readable "Capability / Status" table a customer
    actually reads — the same "Capability | Status" shape the governing
    worked example uses. Shared by `python -m framework.extension analyze`'s
    console output and the scaffold manifest's companion text, so the two
    never drift apart (same "one formatter, multiple callers" precedent as
    `framework.sync.test_inventory.format_inventory`).
    """
    if not items:
        return "REUSE MATRIX\n\n(no extension items)"

    subject_width = max(len("Capability"), *(len(item.subject) for item in items))
    header = f"{'Capability':<{subject_width}}  Status"
    separator = "-" * (subject_width + 2 + max(len("Status"), 15))
    lines = ["REUSE MATRIX", "", header, separator]
    for item in items:
        lines.append(f"{item.subject:<{subject_width}}  {item.classification.value.upper()}")
    return "\n".join(lines)
