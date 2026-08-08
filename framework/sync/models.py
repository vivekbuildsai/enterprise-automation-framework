from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class SupportLevel(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"


class SyncMode(str, Enum):
    """Mode 1 (ANALYZE) and Mode 2 (SCAFFOLD) are implemented
    (`RepositoryAnalyzer`, `generate_migration_worksheet`). Mode 3
    (MIGRATE — generating translated source) and Mode 4 (SYNC —
    diff-driven re-application against an existing target) are
    intentionally NOT implemented: source-to-source code translation
    between automation frameworks is not something that can be done
    safely/genuinely without a much larger, framework-pair-specific
    effort than this session can responsibly deliver and verify. They're
    modeled here as the extension point for that future work — see
    docs/FrameworkSync.md.
    """

    ANALYZE = "analyze"
    SCAFFOLD = "scaffold"
    MIGRATE = "migrate"
    SYNC = "sync"


class DetectedFramework(BaseModel):
    name: str
    category: str
    support_level: SupportLevel
    evidence: list[str] = Field(default_factory=list)
    notes: str = ""


class Finding(BaseModel):
    """A risk/observation surfaced during static analysis — never
    contains the actual secret value, only its location and category.
    """

    category: str
    file: str
    line: int | None = None
    description: str


class RepositoryStructure(BaseModel):
    total_files: int = 0
    test_files: int = 0
    page_object_like_files: int = 0
    config_files: int = 0
    has_docker: bool = False
    has_ci: bool = False
    dependency_files: list[str] = Field(default_factory=list)


class RobotStructure(BaseModel):
    """Structural counts for Robot Framework's own tabular sections
    (`*** Test Cases ***`, `*** Keywords ***`, `*** Settings ***`,
    `*** Variables ***`) — populated only when `.robot`/`.resource` files
    are present. Robot is a keyword-driven DSL, not source code in a
    general-purpose language, so its structure doesn't fit
    `RepositoryStructure`'s file-name-hint heuristics (see
    `framework.sync.robot_analysis`, docs/FrameworkSync.md).
    """

    test_case_count: int = 0
    keyword_count: int = 0
    resource_file_count: int = 0
    library_names: list[str] = Field(default_factory=list)
    variable_count: int = 0
    has_suite_setup: bool = False
    has_suite_teardown: bool = False
    has_test_setup: bool = False
    has_test_teardown: bool = False


class MappingStatus(str, Enum):
    """How a source-technology *concept* relates to a target-technology
    concept — deliberately separate from `SupportLevel` (which grades one
    detected technology against this framework's own stack as a whole).
    `MappingStatus` is used for concept-to-concept migration guidance
    (`CrossLanguageMapping`) and is never a percentage or fabricated
    score — see docs/FrameworkSync.md "Compatibility model".
    """

    DIRECTLY_REUSABLE = "directly_reusable"
    CONCEPTUALLY_MAPPABLE = "conceptually_mappable"
    REQUIRES_ADAPTATION = "requires_adaptation"
    NOT_DETECTED = "not_detected"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class CrossLanguageMapping(BaseModel):
    """One concept-level migration suggestion — e.g. "Robot Framework's
    `SeleniumLibrary` browser-interaction keywords conceptually map onto
    Playwright's `Page`/`Locator` API." Never a claim of automatic
    conversion — see `SyncMode.MIGRATE`'s docstring for why
    source-to-source translation isn't implemented.
    """

    source_technology: str
    concept: str
    target_technology: str
    status: MappingStatus
    manual_action: str


class TestCategory(str, Enum):
    """Evidence-based only — `UNKNOWN` when reliable evidence is absent,
    never guessed. Not all values are mutually exclusive dimensions by
    construction (this mirrors the flat category list customers actually
    asked for): the UI/API/Database (and pairwise) values come from
    import/client evidence within one test's own file; the suite-type
    values (Smoke/Regression/Integration/Unit/EndToEnd) come from
    tag/marker/group text on the test itself. A test is assigned whichever
    single value its strongest available evidence supports.
    """

    UI = "ui"
    API = "api"
    DATABASE = "database"
    UI_API = "ui_api"
    UI_DATABASE = "ui_database"
    API_DATABASE = "api_database"
    END_TO_END = "end_to_end"
    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
    UNIT = "unit"
    UNKNOWN = "unknown"


class Test(BaseModel):
    """One individual detected test — the atomic, traceable unit that
    migration candidates and scope-based selection operate on.
    `identifier` is stable (`<source_file>::<ClassName>::<name>`, or
    `<source_file>::<name>` when there's no containing class/Test Case
    grouping) so a customer can always trace a migration recommendation
    back to its exact original source — see "Migration traceability" in
    docs/FrameworkSync.md. Never claims a file/function is a test without
    framework-specific evidence (see `framework.sync.test_inventory`) —
    a source file is not a test merely because it exists.
    """

    identifier: str
    source_file: str
    name: str
    class_name: str | None = None
    technology: str
    tags: list[str] = Field(default_factory=list)
    category: TestCategory = TestCategory.UNKNOWN


class AutomationInventory(BaseModel):
    """The read-only "what do you already have?" summary — the first
    question this product answers, before any migration question. Every
    count here is backed by framework-specific evidence, never inferred
    from file presence alone. Rendered as the "EXISTING AUTOMATION
    INVENTORY" block in both `analyze`'s console output and the migration
    worksheet — see docs/FrameworkSync.md.
    """

    tests_detected: int = 0
    test_classes: int = 0
    test_suites: int = 0
    tags: list[str] = Field(default_factory=list)
    page_objects: int = 0
    components: int = 0
    reusable_keywords: int = 0
    fixtures: int = 0
    api_clients: int = 0
    database_utilities: int = 0
    test_data_sources: int = 0
    configuration_files: int = 0
    authentication_mechanisms: list[str] = Field(default_factory=list)
    ci_pipeline: str | None = None
    reporting: list[str] = Field(default_factory=list)


class ExecutionModel(BaseModel):
    """The customer's existing execution model, captured for
    understanding — never run. Every field is `None`/empty unless real
    evidence (a build file, CI config, or test-runner config) was found;
    nothing here is inferred from convention alone (e.g. "Java probably
    uses `mvn test`" is not evidence).
    """

    command: str | None = None
    runner: str | None = None
    parallelism: int | None = None
    retries: int | None = None
    environments: list[str] = Field(default_factory=list)
    browser: str | None = None
    reporting: list[str] = Field(default_factory=list)
    test_selection: str | None = None


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class MigrationScope(str, Enum):
    """Granularity at which migration candidates can be selected — the
    entire repository is never the only option; a customer with 1,500
    working tests can ask for guidance on just one directory, suite, tag,
    class, or individual test, leaving everything else untouched (Mode B,
    "Selective Migration" — see docs/FrameworkSync.md).
    """

    REPOSITORY = "repository"
    DIRECTORY = "directory"
    SUITE = "suite"
    TAG = "tag"
    CLASS = "class"
    TEST = "test"


class MigrationCandidate(BaseModel):
    """One individual test's migration guidance, with full provenance —
    never a claim that conversion happened. `status` is always a
    `MappingStatus` (concept-level guidance only) and `reason` always
    explains *why*, never asserts success. See "Migration traceability"
    in docs/FrameworkSync.md.
    """

    test: Test
    technology: str
    target_technology: str
    status: MappingStatus
    risk: RiskLevel
    reason: str


class CapabilityCategory(str, Enum):
    """What kind of reusable automation asset an `ExistingCapability`
    represents — the same categories `AutomationInventory` already
    counts, now surfaced as named, individually addressable entries
    instead of just totals (see framework.sync.capability_catalog).
    """

    API_CLIENT = "api_client"
    DATABASE_UTILITY = "database_utility"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    PAGE_OBJECT = "page_object"
    COMPONENT = "component"
    TEST_DATA = "test_data"
    REPORTING = "reporting"


class ExistingCapability(BaseModel):
    """One named, traceable reusable asset already present in the
    customer's framework — e.g. an API client method with the endpoint
    pattern it calls, or a repository/validator class. `endpoint_pattern`
    (e.g. `/employees/{id}`) and `http_method` are populated only for
    `API_CLIENT` entries where a literal path was actually found next to
    an HTTP-verb call — never guessed. This is the "capability catalog"
    a new UI's discovered network activity gets correlated against (see
    `framework.extension`).
    """

    category: CapabilityCategory
    name: str
    source_file: str
    endpoint_pattern: str | None = None
    http_method: str | None = None
    evidence: str = ""


class CapabilityCatalog(BaseModel):
    capabilities: list[ExistingCapability] = Field(default_factory=list)


class RepositoryAnalysis(BaseModel):
    source: str
    analyzed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    primary_language: str = "unknown"
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    detected_frameworks: list[DetectedFramework] = Field(default_factory=list)
    structure: RepositoryStructure = Field(default_factory=RepositoryStructure)
    robot_structure: RobotStructure | None = None
    tests: list[Test] = Field(default_factory=list)
    inventory: AutomationInventory = Field(default_factory=AutomationInventory)
    execution_model: ExecutionModel | None = None
    capability_catalog: CapabilityCatalog = Field(default_factory=CapabilityCatalog)
    findings: list[Finding] = Field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> RepositoryAnalysis:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class CompatibilityReport(BaseModel):
    """A transparent, inspectable ratio — never a fabricated score. See
    `framework.sync.compatibility.compute_compatibility_report` for the
    exact (documented) formula.
    """

    supported_count: int
    partially_supported_count: int
    manual_review_count: int
    total_detected: int
    compatibility_ratio: float
    summary: str


class AnalysisDiff(BaseModel):
    new_frameworks: list[str] = Field(default_factory=list)
    removed_frameworks: list[str] = Field(default_factory=list)
    file_count_delta: int = 0
    new_findings: list[Finding] = Field(default_factory=list)
    resolved_findings_count: int = 0
