"""Capability catalog extraction — treats the customer's existing
framework as a catalog of *named*, individually addressable reusable
automation assets (API client methods with their endpoint patterns,
DB repositories/tables, validators, Page Objects/components), not just
the aggregate counts `AutomationInventory` already provides. This is
what a new UI's discovered network activity gets correlated against in
`framework.extension` — see docs/FrameworkSync.md, "Existing framework
as a product asset."

Same lightweight regex/token scanning philosophy as the rest of
`framework.sync` — never execution, never a full per-language parser.
Endpoint patterns are only ever reported when a literal path string was
actually found next to an HTTP-verb call; a dynamic segment
(`f"/employees/{id}"`, or a trailing `"/employees/" + id` concatenation)
is normalized to `{param}` for later correlation, never guessed beyond
what the source text shows.
"""

from __future__ import annotations

import re
from pathlib import Path

from framework.sync.models import CapabilityCatalog, CapabilityCategory, ExistingCapability

_CLASS_PATTERN = re.compile(r"\bclass\s+(\w+)")
_PYTHON_METHOD_PATTERN = re.compile(r"^\s*def\s+(\w+)\s*\(")
_JAVA_CSHARP_METHOD_PATTERN = re.compile(
    r"(?:public|private|protected)\s+[\w<>\[\],\s]+?\s+(\w+)\s*\("
)
_HTTP_CALL_PATTERN = re.compile(
    r"\.(get|post|put|patch|delete)\(\s*f?[\"']([^\"']+)[\"']", re.IGNORECASE
)
_HTTP_ANNOTATION_PATTERN = re.compile(
    r"@(Get|Post|Put|Patch|Delete)Mapping\(\s*[\"']([^\"']+)[\"']", re.IGNORECASE
)
_ROBOT_HTTP_KEYWORD_PATTERN = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+On\s+Session\s+\S+\s+(\S+)", re.IGNORECASE
)

_API_CLASS_NAME_HINTS = ("Api", "Client")
_REPOSITORY_CLASS_NAME_HINTS = ("Repository", "Repo", "Dao")
_VALIDATOR_CLASS_NAME_HINTS = ("Validator",)
_TABLENAME_PATTERN = re.compile(r"__tablename__\s*=\s*[\"'](\w+)[\"']")
_TABLE_CALL_PATTERN = re.compile(r"\bTable\(\s*[\"'](\w+)[\"']")
_SQL_KEYWORD_PATTERN = re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_SQL_TABLE_REF_PATTERN = re.compile(
    r"\b(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE
)
_DATA_COMPARATOR_PATTERN = re.compile(r"\bDataComparator\b")
_TEST_DATA_PATH_TOKENS = ("testdata", "test_data", "fixture", "dataset", "seed", "factory")
_REPORTING_TOKENS = ("allure", "reportportal", "extent report", "html report")


def _normalize_path(raw: str) -> str:
    """Any `{...}` interpolation placeholder becomes `{param}`; a literal
    ending in `/` (the common "base path + concatenated id" shape, e.g.
    `"/employees/" + str(id)`) also gets an implicit `{param}` appended —
    both normalizations exist purely so a later *discovered* concrete
    path (`/employees/42`) can be matched against this pattern, never to
    fabricate a path that wasn't actually present in the source.
    """
    normalized = re.sub(r"\{[^}]*\}", "{param}", raw)
    if normalized.endswith("/"):
        normalized = normalized.rstrip("/") + "/{param}"
    return normalized


def _current_method(line: str) -> str | None:
    if match := _PYTHON_METHOD_PATTERN.match(line):
        return match.group(1)
    if match := _JAVA_CSHARP_METHOD_PATTERN.search(line):
        return match.group(1)
    return None


def _extract_api_clients(root: Path, file_contents: dict[Path, str]) -> list[ExistingCapability]:
    found: list[ExistingCapability] = []
    for path, text in file_contents.items():
        relative = str(path.relative_to(root))
        current_class: str | None = None
        current_method: str | None = None

        for line in text.splitlines():
            if class_match := _CLASS_PATTERN.search(line):
                current_class = class_match.group(1)
            if method_name := _current_method(line):
                current_method = method_name

            http_match = _HTTP_CALL_PATTERN.search(line) or _HTTP_ANNOTATION_PATTERN.search(line)
            if not http_match:
                continue
            method, raw_path = http_match.group(1).upper(), http_match.group(2)

            if current_class is None or not any(
                hint in current_class for hint in _API_CLASS_NAME_HINTS
            ):
                continue

            name = f"{current_class}.{current_method}" if current_method else current_class
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.API_CLIENT,
                    name=name,
                    source_file=relative,
                    endpoint_pattern=_normalize_path(raw_path),
                    http_method=method,
                    evidence=line.strip()[:160],
                )
            )

        for robot_match in _ROBOT_HTTP_KEYWORD_PATTERN.finditer(text):
            method, raw_path = robot_match.group(1).upper(), robot_match.group(2)
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.API_CLIENT,
                    name=f"{relative}::{method} On Session",
                    source_file=relative,
                    endpoint_pattern=_normalize_path(raw_path),
                    http_method=method,
                    evidence=robot_match.group(0).strip()[:160],
                )
            )
    return found


def _extract_database_utilities(
    root: Path, file_contents: dict[Path, str]
) -> list[ExistingCapability]:
    found: list[ExistingCapability] = []
    for path, text in file_contents.items():
        relative = str(path.relative_to(root))

        for class_match in _CLASS_PATTERN.finditer(text):
            class_name = class_match.group(1)
            if any(hint in class_name for hint in _REPOSITORY_CLASS_NAME_HINTS):
                found.append(
                    ExistingCapability(
                        category=CapabilityCategory.DATABASE_UTILITY,
                        name=class_name,
                        source_file=relative,
                        evidence=f"class {class_name}",
                    )
                )

        for tablename_match in _TABLENAME_PATTERN.finditer(text):
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.DATABASE_UTILITY,
                    name=f"table:{tablename_match.group(1)}",
                    source_file=relative,
                    evidence=tablename_match.group(0),
                )
            )
        for table_call_match in _TABLE_CALL_PATTERN.finditer(text):
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.DATABASE_UTILITY,
                    name=f"table:{table_call_match.group(1)}",
                    source_file=relative,
                    evidence=table_call_match.group(0),
                )
            )
        for line in text.splitlines():
            if not _SQL_KEYWORD_PATTERN.search(line):
                continue
            for table_ref_match in _SQL_TABLE_REF_PATTERN.finditer(line):
                found.append(
                    ExistingCapability(
                        category=CapabilityCategory.DATABASE_UTILITY,
                        name=f"table:{table_ref_match.group(1)}",
                        source_file=relative,
                        evidence=line.strip()[:160],
                    )
                )
    return found


def _extract_validators(root: Path, file_contents: dict[Path, str]) -> list[ExistingCapability]:
    found: list[ExistingCapability] = []
    for path, text in file_contents.items():
        relative = str(path.relative_to(root))
        for class_match in _CLASS_PATTERN.finditer(text):
            class_name = class_match.group(1)
            if any(hint in class_name for hint in _VALIDATOR_CLASS_NAME_HINTS):
                found.append(
                    ExistingCapability(
                        category=CapabilityCategory.VALIDATION,
                        name=class_name,
                        source_file=relative,
                        evidence=f"class {class_name}",
                    )
                )
        if _DATA_COMPARATOR_PATTERN.search(text):
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.VALIDATION,
                    name="DataComparator",
                    source_file=relative,
                    evidence="DataComparator usage",
                )
            )
    return found


def _extract_page_objects_and_components(
    root: Path, file_contents: dict[Path, str], page_object_hints: tuple[str, ...]
) -> list[ExistingCapability]:
    found: list[ExistingCapability] = []
    for path, text in file_contents.items():
        if not any(hint in path.name for hint in page_object_hints):
            continue
        relative = str(path.relative_to(root))
        class_match = _CLASS_PATTERN.search(text)
        if not class_match:
            continue
        category = (
            CapabilityCategory.COMPONENT
            if "component" in path.name.lower()
            else CapabilityCategory.PAGE_OBJECT
        )
        found.append(
            ExistingCapability(
                category=category,
                name=class_match.group(1),
                source_file=relative,
                evidence=f"class {class_match.group(1)}",
            )
        )
    return found


def _extract_authentication(
    authentication_mechanisms: list[str],
) -> list[ExistingCapability]:
    # Reuses `AutomationInventory.authentication_mechanisms` (already
    # computed by `framework.sync.test_inventory`) rather than
    # re-deriving the same evidence a second time.
    return [
        ExistingCapability(
            category=CapabilityCategory.AUTHENTICATION,
            name=mechanism,
            source_file="",
            evidence=f"{mechanism} mentioned in repository",
        )
        for mechanism in authentication_mechanisms
    ]


def _extract_test_data_and_reporting(
    root: Path, file_contents: dict[Path, str]
) -> list[ExistingCapability]:
    """Surface real test-data/reporting assets as individually traceable
    catalog entries.  These are deliberately simple source/path indicators:
    they say an asset exists, not that it is compatible with a new UI.
    """
    found: list[ExistingCapability] = []
    for path, text in file_contents.items():
        relative = str(path.relative_to(root))
        lowered_path = relative.lower()
        lowered_text = text.lower()
        if any(token in lowered_path for token in _TEST_DATA_PATH_TOKENS):
            found.append(
                ExistingCapability(
                    category=CapabilityCategory.TEST_DATA,
                    name=f"test-data:{Path(relative).stem}",
                    source_file=relative,
                    evidence="test-data path convention",
                )
            )
        for token in _REPORTING_TOKENS:
            if path.suffix not in (".md", ".txt") and token in lowered_text:
                found.append(
                    ExistingCapability(
                        category=CapabilityCategory.REPORTING,
                        name=token.replace(" ", "_").title().replace("_", ""),
                        source_file=relative,
                        evidence=f"'{token}' found in source",
                    )
                )
                break
    return found


def build_capability_catalog(
    root: Path,
    file_contents: dict[Path, str],
    *,
    authentication_mechanisms: list[str],
    page_object_hints: tuple[str, ...],
) -> CapabilityCatalog:
    capabilities: list[ExistingCapability] = []
    capabilities.extend(_extract_api_clients(root, file_contents))
    capabilities.extend(_extract_database_utilities(root, file_contents))
    capabilities.extend(_extract_validators(root, file_contents))
    capabilities.extend(
        _extract_page_objects_and_components(root, file_contents, page_object_hints)
    )
    capabilities.extend(_extract_authentication(authentication_mechanisms))
    capabilities.extend(_extract_test_data_and_reporting(root, file_contents))
    return CapabilityCatalog(capabilities=capabilities)
