"""Data shapes for the environment doctor (`framework.doctor`) — a
read-only capability inventory of the host machine, structurally the same
"evidence-based, never fabricated" discipline the rest of this framework
already uses for `framework.sync`/`framework.discovery`/`framework.extension`.
Every `EnvironmentCapability` traces back to a real, observed check (a
`shutil.which()` hit, a `--version` subprocess call, a real file on disk)
— never a guess.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    """Never just true/false — a capability can be present but not the
    one selected (`AVAILABLE` + not chosen), legitimately unneeded
    (`NOT_REQUIRED`), or present-but-broken (`DEGRADED`), each of which
    calls for different user-facing guidance.
    """

    AVAILABLE = "available"
    MISSING = "missing"
    DEGRADED = "degraded"
    UNSUPPORTED = "unsupported"
    NOT_REQUIRED = "not_required"
    BLOCKED = "blocked"


class CapabilityCategory(str, Enum):
    OPERATING_SYSTEM = "operating_system"
    PYTHON = "python"
    NODE = "node"
    BROWSER = "browser"
    FFMPEG = "ffmpeg"
    DOCKER = "docker"
    GIT = "git"


class EnvironmentCapability(BaseModel):
    """One detected (or explicitly not-detected) fact about the host
    environment. `required`/`optional` are independent of `available` —
    an optional, missing tool is `NOT_REQUIRED`/`MISSING` but never a
    doctor failure; a required, missing one is `MISSING` and blocks
    `--check`.
    """

    name: str
    category: CapabilityCategory
    available: bool
    version: str | None = None
    path: str | None = None
    required: bool = False
    status: CapabilityStatus
    reason: str = ""
    remediation: str = ""


class DoctorReport(BaseModel):
    """The full capability matrix for one doctor run — JSON is the
    machine-readable artifact; `framework.doctor.report` renders the
    human-readable console summary from the same data, so the two can
    never drift apart.
    """

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    capabilities: list[EnvironmentCapability] = Field(default_factory=list)
    recommended_browser: str | None = None
    recommendation_reason: str = ""

    @property
    def required_missing(self) -> list[EnvironmentCapability]:
        return [c for c in self.capabilities if c.required and not c.available]

    @property
    def passed(self) -> bool:
        return not self.required_missing

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> DoctorReport:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
