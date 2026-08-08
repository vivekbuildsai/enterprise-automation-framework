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
    """

    discovered_call: DiscoveredNetworkCall
    matched_capability: ExistingCapability | None = None
    status: RelationshipStatus
    evidence: list[str] = Field(default_factory=list)


class ExtensionItem(BaseModel):
    """One row of the "EXISTING FRAMEWORK EXTENSION REPORT" — a single
    discovered new-UI subject (a page, an API dependency, a data
    dependency, ...) paired with a classification and, where applicable,
    the existing capability it reuses or extends. `reason` always
    explains the classification in plain language; `evidence` holds the
    lower-level supporting facts (mirrors `MigrationCandidate.reason` in
    `framework.sync.models` — never a bare label with no justification).
    """

    subject: str
    subject_type: ExtensionSubjectType
    classification: ExtensionClassification
    matched_capability: ExistingCapability | None = None
    reason: str
    evidence: list[str] = Field(default_factory=list)


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


class ExtensionReport(BaseModel):
    """The full output of the extension-analysis pipeline — the
    "what already exists, what does the new UI need, what can be reused"
    artifact a human reviews before anything is built (same "report is
    the checkpoint" precedent as `framework.discovery.models.DiscoveryReport`
    and `framework.sync.models.RepositoryAnalysis`). Never implies any
    modification happened to the existing repository or the new UI.
    """

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    existing_framework_source: str = ""
    new_ui_source: str = ""
    correlations: list[UIAPICorrelation] = Field(default_factory=list)
    extension_items: list[ExtensionItem] = Field(default_factory=list)
    test_opportunities: list[TestOpportunity] = Field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> ExtensionReport:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
