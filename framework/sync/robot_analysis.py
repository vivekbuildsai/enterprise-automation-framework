"""Lightweight, evidence-based structural analysis of Robot Framework
source files (`.robot`/`.resource`).

Robot Framework is a keyword-driven automation DSL, not source code in a
general-purpose language — its `*** Section ***` tabular format is simple
and stable enough that line-based regex parsing is sufficient; this
deliberately does not pull in a full Robot AST/parsing library (see
docs/FrameworkSync.md, "Multi-Language & Multi-Framework Framework Sync").
Never executes anything — pure text analysis, exactly like the rest of
`framework.sync`.
"""

from __future__ import annotations

import re

from framework.sync.models import RobotStructure

_SECTION_HEADER = re.compile(r"^\*{3,}\s*(.+?)\s*\*{3,}\s*$")
_SETTING_LIBRARY = re.compile(r"^Library\s+(\S+)", re.IGNORECASE)
_SETTING_SUITE_SETUP = re.compile(r"^Suite Setup\s+\S", re.IGNORECASE)
_SETTING_SUITE_TEARDOWN = re.compile(r"^Suite Teardown\s+\S", re.IGNORECASE)
_SETTING_TEST_SETUP = re.compile(r"^Test Setup\s+\S", re.IGNORECASE)
_SETTING_TEST_TEARDOWN = re.compile(r"^Test Teardown\s+\S", re.IGNORECASE)
_VARIABLE_NAME = re.compile(r"^[$@&]\{[^}]+\}")
_TAGS_SETTING = re.compile(r"^\[Tags\]\s+(.+)$", re.IGNORECASE)

# Robot Framework's own section-name aliases (plural/singular, `Tasks` is
# the Robot Framework "task" flavor of `Test Cases`, same tabular shape).
_KNOWN_SECTIONS = {
    "settings": "settings",
    "setting": "settings",
    "test cases": "test_cases",
    "test case": "test_cases",
    "tasks": "test_cases",
    "task": "test_cases",
    "keywords": "keywords",
    "keyword": "keywords",
    "variables": "variables",
    "variable": "variables",
}


def _apply_settings_line(structure: RobotStructure, line: str) -> None:
    if (m := _SETTING_LIBRARY.match(line)) is not None:
        structure.library_names.append(m.group(1))
    elif _SETTING_SUITE_SETUP.match(line):
        structure.has_suite_setup = True
    elif _SETTING_SUITE_TEARDOWN.match(line):
        structure.has_suite_teardown = True
    elif _SETTING_TEST_SETUP.match(line):
        structure.has_test_setup = True
    elif _SETTING_TEST_TEARDOWN.match(line):
        structure.has_test_teardown = True


def analyze_robot_file(text: str) -> RobotStructure:
    """Parses one `.robot`/`.resource` file's text into structural
    counts. Merge multiple files' results with `merge_robot_structures`.
    """
    structure = RobotStructure()
    section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = _SECTION_HEADER.match(line)
        if header_match:
            section = _KNOWN_SECTIONS.get(header_match.group(1).strip().lower())
            continue
        if section is None:
            continue

        # Robot's own tabular convention: a Test Case/Keyword *name* starts
        # at column 0 (no leading whitespace); its steps are indented
        # under it. `raw_line` (not the stripped `line`) is checked here
        # specifically to preserve that leading-whitespace signal.
        is_item_start = not raw_line[:1].isspace()

        if section == "settings":
            _apply_settings_line(structure, line)
        elif section == "test_cases" and is_item_start:
            structure.test_case_count += 1
        elif section == "keywords" and is_item_start:
            structure.keyword_count += 1
        elif section == "variables" and is_item_start and _VARIABLE_NAME.match(line):
            structure.variable_count += 1

    return structure


def extract_robot_tests(text: str) -> list[tuple[str, list[str]]]:
    """Parses one `.robot` file's `*** Test Cases ***` section into
    `(name, tags)` pairs — the per-test-case counterpart to
    `analyze_robot_file`'s aggregate `test_case_count`. A `[Tags]` line
    (Robot's own per-test-case setting, e.g. `[Tags]    smoke`) found
    among a test case's indented steps is associated with that test case;
    a test case with no `[Tags]` line gets an empty tag list, never a
    guessed one.
    """
    tests: list[tuple[str, list[str]]] = []
    section: str | None = None
    current_name: str | None = None
    current_tags: list[str] = []

    def _flush() -> None:
        if current_name is not None:
            tests.append((current_name, current_tags))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = _SECTION_HEADER.match(line)
        if header_match:
            _flush()
            current_name, current_tags = None, []
            section = _KNOWN_SECTIONS.get(header_match.group(1).strip().lower())
            continue
        if section != "test_cases":
            continue

        is_item_start = not raw_line[:1].isspace()
        if is_item_start:
            _flush()
            current_name, current_tags = line, []
            continue

        if current_name is not None and (tags_match := _TAGS_SETTING.match(line)):
            current_tags = [
                t.strip() for t in re.split(r"\s{2,}|\t", tags_match.group(1)) if t.strip()
            ]

    _flush()
    return tests


def merge_robot_structures(structures: list[RobotStructure]) -> RobotStructure:
    """Combines per-file `RobotStructure` results into one repository-wide
    total. `library_names` is deduplicated (order-preserving) — the same
    library is typically imported by multiple `.robot`/`.resource` files.
    """
    merged = RobotStructure()
    seen_libraries: list[str] = []

    for item in structures:
        merged.test_case_count += item.test_case_count
        merged.keyword_count += item.keyword_count
        merged.variable_count += item.variable_count
        merged.has_suite_setup = merged.has_suite_setup or item.has_suite_setup
        merged.has_suite_teardown = merged.has_suite_teardown or item.has_suite_teardown
        merged.has_test_setup = merged.has_test_setup or item.has_test_setup
        merged.has_test_teardown = merged.has_test_teardown or item.has_test_teardown
        for library in item.library_names:
            if library not in seen_libraries:
                seen_libraries.append(library)

    merged.library_names = seen_libraries
    return merged
