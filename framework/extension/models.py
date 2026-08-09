"""Bridging models for the "new UI + existing API + existing database"
extension capability — the layer that sits *between* `framework.sync`'s
capability catalog (what the existing framework already has) and
`framework.discovery`'s new-UI discovery (what a brand-new, zero-test UI
actually does), and answers the customer's real question: what can be
reused, what needs extending, and what genuinely needs to be built?

Every model here is evidence-based, same as the rest of this framework:
a `RelationshipStatus`/`ExtensionClassification` is never assigned without
recording *why* (`evidence`), and `UNKNOWN`/`MANUAL_REVIEW` are real,
expected outcomes — not something to be optimized away. Nothing in this
package modifies the customer's existing 1,500-test repository or the new
UI; it only reads (via `framework.sync`/`framework.discovery`) and
produces a report for a human to review — see docs/FrameworkSync.md,
"Existing framework as a product asset."
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from framework.discovery.models import DiscoveredNetworkCall
from framework.sync.models import ExistingCapability


class RelationshipStatus(str, Enum):
    """How confidently a discovered new-UI network call maps onto an
    existing API capability. `LIKELY_REUSABLE` requires multiple
    independent signals (endpoint pattern match + HTTP method match, at
    minimum) — never assigned from a single weak signal alone.
    `NOT_FOUND` means no existing capability matched at all (a genuine
    `CREATE_NEW` candidate); `MANUAL_REVIEW` means the evidence was too
    ambiguous to call automatically (e.g. multiple equally-plausible
    matches) — see `framework.extension.correlation`.
    """

    LIKELY_REUSABLE = "likely_reusable"
    POSSIBLY_REUSABLE = "possibly_reusable"
    NOT_FOUND = "not_found"
    MANUAL_REVIEW = "manual_review"


class ExtensionClassification(str, Enum):
    """The per-item verdict in the "EXISTING FRAMEWORK EXTENSION REPORT" —
    never a claim of automatic action. `REUSE_EXISTING` and
    `EXTEND_EXISTING` both point at a real `ExistingCapability`;
    `CREATE_NEW` means no matching capability exists at all;
    `MANUAL_REVIEW` means the evidence doesn't clearly support any of the
    other three. `UNKNOWN` is reserved for items that could not be
    evaluated at all (e.g. discovery data was incomplete for this item) —
    distinct from `MANUAL_REVIEW`, which means evaluation happened but was
    inconclusive.
    """

    REUSE_EXISTING = "reuse_existing"
    EXTEND_EXISTING = "extend_existing"
    CREATE_NEW = "create_new"
    UNKNOWN = "unknown"
    MANUAL_REVIEW = "manual_review"


class ExtensionSubjectType(str, Enum):
    """What kind of discovered new-UI subject one `ExtensionItem`
    describes — the same shape a customer's own "UI Page / Login /
    Employee API / DB connection / Reporting" worked-example table uses.
    """

    UI_PAGE = "ui_page"
    UI_COMPONENT = "ui_component"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    TEST_DATA = "test_data"
    REPORTING = "reporting"
    OTHER = "other"


class UIAPICorrelation(BaseModel):
    """One discovered new-UI network call, correlated against the
    existing framework's capability catalog. `matched_capability` is
    `None` whenever `status` is `NOT_FOUND` — a correlation is never
    reported as a match without a capability to point at. `evidence`
    lists the concrete signals that led to `status` (e.g. "endpoint
    pattern match", "HTTP method match", "query parameter name overlap")
    so a human reviewer can verify the reasoning, not just trust a label.
    `confidence` (0-100, additive field, defaults to 0 for any caller that
    predates it) is a deterministic function of `status` and how many
    signals in `evidence` agree — see
    `framework.extension.correlation._confidence_for_status` — never a
    separate, independently-assigned guess that could disagree with the
    evidence next to it.
    """

    discovered_call: DiscoveredNetworkCall
    matched_capability: ExistingCapability | None = None
    status: RelationshipStatus
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class ExtensionItem(BaseModel):
    """One row of the "EXISTING FRAMEWORK EXTENSION REPORT" — a single
    discovered new-UI subject (a page, an API dependency, a data
    dependency, ...) paired with a classification and, where applicable,
    the existing capability it reuses or extends. `reason` always
    explains the classification in plain language; `evidence` holds the
    lower-level supporting facts (mirrors `MigrationCandidate.reason` in
    `framework.sync.models` — never a bare label with no justification).
    `confidence` (0-100, additive field, defaults to 0) carries the same
    meaning as `UIAPICorrelation.confidence` — for items built directly
    from a correlation it is copied through unchanged; for items with no
    underlying correlation (a page, the aggregate authentication item, a
    shared-infrastructure item) it reflects how confident the
    classification itself is, not a match strength — see
    `framework.extension.gap_analysis._confidence_for_classification`.
    """

    subject: str
    subject_type: ExtensionSubjectType
    classification: ExtensionClassification
    matched_capability: ExistingCapability | None = None
    reason: str
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)


class TestOpportunity(BaseModel):
    """One named, user-facing action opportunity derived from the new UI's
    discovery data (e.g. "Employee Search", "Login") — deliberately not a
    generated test case. `suggested_scenario_types` are advisory labels
    only (happy_path/validation/boundary/negative/authorization/
    ui_api_consistency/ui_api_db_consistency) — see the "Test case
    generation boundary" requirement in docs/FrameworkSync.md: this
    product inventories opportunities, it does not auto-invent test
    cases.
    """

    name: str
    page_url: str
    related_elements: list[str] = Field(default_factory=list)
    related_api_paths: list[str] = Field(default_factory=list)
    suggested_scenario_types: list[str] = Field(default_factory=list)


class ScaffoldTarget(str, Enum):
    """Which of the customer's own automation ecosystems generated
    scaffold code should be written in — detected from the existing
    framework's own `RepositoryAnalysis` (primary language + detected
    frameworks/test runners), never guessed or defaulted to this
    framework's own Python/pytest/Playwright stack. `UNKNOWN` is a real,
    honest outcome (e.g. C#, Cypress-only, or an undetectable repository)
    — the scaffold generator writes a manifest/README only for it, never
    fabricated code in a language nobody asked for.
    """

    JAVA_SELENIUM_TESTNG = "java_selenium_testng"
    JAVA_SELENIUM_JUNIT = "java_selenium_junit"
    PYTHON_PYTEST_PLAYWRIGHT = "python_pytest_playwright"
    TYPESCRIPT_PLAYWRIGHT = "typescript_playwright"
    ROBOT_FRAMEWORK = "robot_framework"
    UNKNOWN = "unknown"


class ScaffoldFileKind(str, Enum):
    PAGE_OBJECT = "page_object"
    COMPONENT = "component"
    TEST = "test"
    RESOURCE = "resource"
    README = "readme"


class ScaffoldFile(BaseModel):
    """One file the scaffold generator proposes writing — a plan entry,
    not yet a write. `relative_path` is always relative to the scaffold
    output directory (never absolute, never containing `..`) — enforced
    by `framework.extension.paths` before anything reaches disk.
    """

    relative_path: str
    kind: ScaffoldFileKind
    content: str


class ScaffoldManifest(BaseModel):
    """The human-reviewable record of one scaffold run — deliberately
    excludes file *content* (that's in the files themselves) so this stays
    small and diffable. Never claims the generated code is "production
    ready"; `confidence` is always an honest, review-required label (see
    `framework.extension.scaffold._SCAFFOLD_NOTICE`). Contains no secrets:
    every field here is a path, a capability name, or a classification
    label, never a captured value.
    """

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    existing_framework_source: str = ""
    new_ui_source: str = ""
    target: ScaffoldTarget = ScaffoldTarget.UNKNOWN
    confidence: str = "scaffold — review required, not executed or validated"
    files: list[str] = Field(default_factory=list)
    reused_capabilities: list[str] = Field(default_factory=list)
    newly_generated_capabilities: list[str] = Field(default_factory=list)
    manual_review_items: list[str] = Field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> ScaffoldManifest:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class NetworkCallClassification(str, Enum):
    """What a discovered network call actually *is*, before it's ever
    handed to correlation — the missing stage that let CSS/JS/image
    requests and login-page assets get treated as application capability
    evidence. Every value here is assigned from real, inspectable
    evidence (a file extension, a path segment, a hostname, a body
    shape) — never a default guess; `UNKNOWN` is the honest fallback when
    none of the classification rules matched with confidence.
    """

    APPLICATION_API = "application_api"
    AUTHENTICATION = "authentication"
    STATIC_ASSET = "static_asset"
    FRAMEWORK_ASSET = "framework_asset"
    ANALYTICS = "analytics"
    THIRD_PARTY = "third_party"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class ClassifiedNetworkCall(BaseModel):
    """One discovered network call after classification + deduplication —
    `duplicate_count` is 1 for a call with no duplicates, >1 when N raw
    calls collapsed into this single entry (see
    `framework.extension.network_classification`).
    """

    call: DiscoveredNetworkCall
    classification: NetworkCallClassification
    reason: str
    duplicate_count: int = 1


class NetworkClassificationSummary(BaseModel):
    """Every count here must trace back to a real `len()` over the actual
    input/output lists — never an invented or estimated number (the
    governing requirement this model exists to satisfy: "use actual
    counts, not invented values").
    """

    raw_count: int = 0
    duplicates_removed: int = 0
    static_or_framework_ignored: int = 0
    analytics_ignored: int = 0
    third_party_ignored: int = 0
    document_ignored: int = 0
    authentication_count: int = 0
    application_candidate_count: int = 0
    unknown_count: int = 0


class NetworkClassificationResult(BaseModel):
    """The full RAW -> NORMALIZE -> DEDUPLICATE -> CLASSIFY output.
    `raw_calls` is kept in full (nothing is ever deleted from the raw
    discovery data — see the module docstring) even though only
    `classified_calls` (deduplicated) is what `framework.extension.correlation`
    should actually consume.
    """

    raw_calls: list[DiscoveredNetworkCall] = Field(default_factory=list)
    classified_calls: list[ClassifiedNetworkCall] = Field(default_factory=list)
    summary: NetworkClassificationSummary = Field(default_factory=NetworkClassificationSummary)

    def application_and_auth_calls(self) -> list[DiscoveredNetworkCall]:
        """The only subset correlation should ever look at — application
        API traffic and authentication endpoints, never static/framework/
        analytics/third-party noise.
        """
        return [
            entry.call
            for entry in self.classified_calls
            if entry.classification
            in (NetworkCallClassification.APPLICATION_API, NetworkCallClassification.AUTHENTICATION)
        ]


class LoginPageSignal(BaseModel):
    """Whether one discovered page looks like a login/authentication page
    rather than genuine application content — the missing check that let
    a login-page redirect get reported as successful discovery of the
    customer's actual target page. `evidence` always lists the concrete
    signals (URL path, page title, a password-type input field) that led
    to the verdict; an empty `evidence` list is why `is_likely_login_page`
    is `False`, never an unexplained guess.
    """

    page_url: str
    is_likely_login_page: bool
    evidence: list[str] = Field(default_factory=list)


class DiscoveryQualityLevel(str, Enum):
    """How much a human should trust a discovery run before scaffolding
    from it — the honesty check the governing philosophy requires
    ("ANALYZE FIRST -> CLASSIFY SECOND -> CORRELATE THIRD -> REVIEW
    FOURTH -> SCAFFOLD LAST"). `BLOCKED` is a real, expected outcome (e.g.
    the only page discovered was a login page) — see
    `framework.extension.discovery_quality`.
    """

    HIGH_CONFIDENCE = "high_confidence"
    PARTIAL = "partial"
    LOW_CONFIDENCE = "low_confidence"
    BLOCKED = "blocked"


class DiscoveryQualityScore(BaseModel):
    """A 0-100 score plus the honest, human-readable reasons behind it —
    never a bare number. `reasons` always explains every point lost, the
    same "never a bare label" precedent `UIAPICorrelation.evidence` and
    `ExtensionItem.evidence` already follow.
    """

    score: int = 0
    level: DiscoveryQualityLevel = DiscoveryQualityLevel.BLOCKED
    reasons: list[str] = Field(default_factory=list)


class ExtensionReport(BaseModel):
    """The full output of the extension-analysis pipeline — the
    "what already exists, what does the new UI need, what can be reused"
    artifact a human reviews before anything is built (same "report is
    the checkpoint" precedent as `framework.discovery.models.DiscoveryReport`
    and `framework.sync.models.RepositoryAnalysis`). Never implies any
    modification happened to the existing repository or the new UI.
    `network_classification`/`discovery_quality` are additive fields
    (default `None`) so a report saved before this milestone still loads
    cleanly — `correlations` is always built from
    `network_classification.application_and_auth_calls()` when a
    classification is available, never from the unfiltered raw calls (see
    `framework.extension.__main__._cmd_analyze`).
    """

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    existing_framework_source: str = ""
    new_ui_source: str = ""
    correlations: list[UIAPICorrelation] = Field(default_factory=list)
    extension_items: list[ExtensionItem] = Field(default_factory=list)
    test_opportunities: list[TestOpportunity] = Field(default_factory=list)
    network_classification: NetworkClassificationResult | None = None
    discovery_quality: DiscoveryQualityScore | None = None

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> ExtensionReport:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
