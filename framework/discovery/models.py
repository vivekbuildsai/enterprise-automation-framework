from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DiscoveredLocator(BaseModel):
    """A locator the discovery engine actually observed — never a guess.
    `strategy` follows the same priority `framework.locators.Locators`
    already encodes (test_id > role > label > css); the discovery engines
    only emit a locator when one of these genuinely stable strategies
    applies, never an `nth-child`/xpath-position fallback.
    """

    strategy: str
    value: str
    role: str | None = None
    accessible_name: str | None = None


class DiscoveredElement(BaseModel):
    tag: str
    element_type: str
    text: str = ""
    locator: DiscoveredLocator
    attributes: dict[str, str] = Field(default_factory=dict)


class DiscoveredPage(BaseModel):
    url: str
    title: str = ""
    elements: list[DiscoveredElement] = Field(default_factory=list)


class DiscoveredEndpoint(BaseModel):
    method: str
    path: str
    summary: str = ""
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None


class DiscoveredColumn(BaseModel):
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False


class DiscoveredTable(BaseModel):
    name: str
    columns: list[DiscoveredColumn] = Field(default_factory=list)
    foreign_keys: list[str] = Field(default_factory=list)


class DiscoveryReport(BaseModel):
    """The intermediate artifact a human reviews before any code gets
    generated — every discovery engine writes into one of these, and
    `code_generator` only ever reads from it, never from a live
    application directly. Keeping this as a plain, inspectable JSON file
    is the "human review" checkpoint: read the report, delete anything
    wrong or unwanted, then generate.
    """

    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    source: str = ""
    pages: list[DiscoveredPage] = Field(default_factory=list)
    endpoints: list[DiscoveredEndpoint] = Field(default_factory=list)
    tables: list[DiscoveredTable] = Field(default_factory=list)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> DiscoveryReport:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
