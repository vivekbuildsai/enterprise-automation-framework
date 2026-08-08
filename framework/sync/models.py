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


class RepositoryAnalysis(BaseModel):
    source: str
    analyzed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    primary_language: str = "unknown"
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    detected_frameworks: list[DetectedFramework] = Field(default_factory=list)
    structure: RepositoryStructure = Field(default_factory=RepositoryStructure)
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
