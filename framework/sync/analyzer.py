from __future__ import annotations

import re
from pathlib import Path

from framework.logger import get_logger
from framework.sync.capability_catalog import build_capability_catalog
from framework.sync.detectors import DEFAULT_ADAPTERS, FrameworkAdapter
from framework.sync.execution_model import detect_execution_model
from framework.sync.models import Finding, RepositoryAnalysis, RepositoryStructure, RobotStructure
from framework.sync.robot_analysis import analyze_robot_file, merge_robot_structures
from framework.sync.test_inventory import build_inventory, extract_tests

_logger = get_logger("RepositoryAnalyzer")

_TEXT_EXTENSIONS = {
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".cs",
    ".csproj",
    ".sln",
    ".robot",
    ".resource",
    ".json",
    ".xml",
    ".gradle",
    ".kts",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".txt",
    ".md",
}
_IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    ".tox",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
# Robot Framework is deliberately its own bucket, not folded into an
# existing language — it's a keyword-driven automation DSL, not source
# code in any general-purpose language (see docs/FrameworkSync.md,
# "Multi-Language & Multi-Framework"). `.resource` files share the same
# tabular syntax as `.robot` files, so they count toward the same bucket.
_LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".cs": "C#",
    ".robot": "Robot Framework",
    ".resource": "Robot Framework",
}
_SOURCE_EXTENSIONS = {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".cs", ".robot", ".resource"}
_TEST_FILE_HINTS = (
    "test_",
    "_test.",
    ".spec.",
    "spec.",
    "Test.java",
    "Tests.java",
    "Test.cs",
    "Tests.cs",
)
_PAGE_OBJECT_HINTS = (
    "page.py",
    "Page.java",
    "Page.ts",
    "Page.cs",
    "page_object",
    "PageObject",
    "Page.js",
)
_DEPENDENCY_FILE_NAMES = (
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
)
_DEPENDENCY_FILE_SUFFIXES = (".csproj", ".sln")
_ROBOT_SUFFIXES = (".robot", ".resource")

_CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*['\"][^'\"]{3,}['\"]"
)
_AWS_KEY_PATTERN = re.compile(r"AKIA[0-9A-Z]{16}")
_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+")
_URL_IGNORE_TOKENS = ("example.com", "localhost", "127.0.0.1", "schema.org", "w3.org")


class RepositoryAnalyzer:
    """Read-only, static analysis only — never executes anything found in
    the target repository. Mode 1 (ANALYZE) of the Existing Framework
    Sync capability.
    """

    def __init__(self, adapters: list[FrameworkAdapter] | None = None) -> None:
        self._adapters = adapters if adapters is not None else DEFAULT_ADAPTERS

    def analyze(self, root: Path, *, source: str) -> RepositoryAnalysis:
        root = Path(root)
        files = self._collect_files(root)
        contents = self._read_text_files(files)

        language_breakdown = self._language_breakdown(files)
        primary_language = (
            max(language_breakdown, key=lambda lang: language_breakdown[lang])
            if language_breakdown
            else "unknown"
        )

        detected = [
            result
            for adapter in self._adapters
            if (result := adapter.detect(root, contents)) is not None
        ]

        structure = self._structure(root, files)
        robot_structure = self._robot_structure(contents)
        findings = self._scan_findings(root, contents)

        tests = extract_tests(root, contents)
        inventory = build_inventory(
            root,
            contents,
            tests,
            robot_structure,
            structure.page_object_like_files,
            structure.config_files,
        )
        execution_model = detect_execution_model(contents)
        capability_catalog = build_capability_catalog(
            root,
            contents,
            authentication_mechanisms=inventory.authentication_mechanisms,
            page_object_hints=_PAGE_OBJECT_HINTS,
        )

        analysis = RepositoryAnalysis(
            source=source,
            primary_language=primary_language,
            language_breakdown=language_breakdown,
            detected_frameworks=detected,
            structure=structure,
            robot_structure=robot_structure,
            tests=tests,
            inventory=inventory,
            execution_model=execution_model,
            capability_catalog=capability_catalog,
            findings=findings,
        )
        _logger.info(
            f"Analyzed {structure.total_files} files ({primary_language}) — "
            f"{len(detected)} framework(s), {inventory.tests_detected} test(s), "
            f"{len(findings)} finding(s)"
        )
        return analysis

    def _collect_files(self, root: Path) -> list[Path]:
        # `path.is_file()` follows symlinks — a malicious cloned repository
        # could contain one pointing outside itself (e.g. at a device file
        # or an unrelated local file), so symlinks are excluded up front
        # rather than silently followed and read.
        return [
            path
            for path in root.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not any(part in _IGNORED_DIRS for part in path.parts)
        ]

    def _read_text_files(self, files: list[Path]) -> dict[Path, str]:
        contents: dict[Path, str] = {}
        for path in files:
            if path.suffix not in _TEXT_EXTENSIONS:
                continue
            try:
                contents[path] = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
        return contents

    def _language_breakdown(self, files: list[Path]) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for path in files:
            language = _LANGUAGE_EXTENSIONS.get(path.suffix)
            if language:
                breakdown[language] = breakdown.get(language, 0) + 1
        return breakdown

    def _structure(self, root: Path, files: list[Path]) -> RepositoryStructure:
        return RepositoryStructure(
            total_files=len(files),
            test_files=sum(1 for f in files if any(h in f.name for h in _TEST_FILE_HINTS)),
            page_object_like_files=sum(
                1 for f in files if any(h in f.name for h in _PAGE_OBJECT_HINTS)
            ),
            config_files=sum(
                1
                for f in files
                if f.suffix in (".yaml", ".yml", ".toml", ".ini", ".cfg")
                or f.name in ("pytest.ini", "package.json", "pom.xml")
            ),
            has_docker=any(
                f.name in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml") for f in files
            ),
            has_ci=any(
                ".github/workflows" in str(f.relative_to(root))
                or f.name in ("Jenkinsfile", ".gitlab-ci.yml")
                for f in files
            ),
            dependency_files=[
                str(f.relative_to(root))
                for f in files
                if f.name in _DEPENDENCY_FILE_NAMES or f.suffix in _DEPENDENCY_FILE_SUFFIXES
            ],
        )

    def _robot_structure(self, contents: dict[Path, str]) -> RobotStructure | None:
        robot_paths = [path for path in contents if path.suffix in _ROBOT_SUFFIXES]
        if not robot_paths:
            return None

        merged = merge_robot_structures(
            [analyze_robot_file(contents[path]) for path in robot_paths]
        )
        merged.resource_file_count = sum(1 for path in robot_paths if path.suffix == ".resource")
        return merged

    def _scan_findings(self, root: Path, contents: dict[Path, str]) -> list[Finding]:
        findings: list[Finding] = []
        for path, text in contents.items():
            relative = str(path.relative_to(root))
            for line_no, line in enumerate(text.splitlines(), start=1):
                if _CREDENTIAL_PATTERN.search(line) or _AWS_KEY_PATTERN.search(line):
                    findings.append(
                        Finding(
                            category="hardcoded_credential",
                            file=relative,
                            line=line_no,
                            description=(
                                "Line matches a hardcoded-credential pattern — value not logged."
                            ),
                        )
                    )
                elif (
                    path.suffix in _SOURCE_EXTENSIONS
                    and _URL_PATTERN.search(line)
                    and not any(token in line for token in _URL_IGNORE_TOKENS)
                ):
                    findings.append(
                        Finding(
                            category="hardcoded_url",
                            file=relative,
                            line=line_no,
                            description=(
                                "Hardcoded URL literal in source — consider externalizing "
                                "to configuration."
                            ),
                        )
                    )
        return findings
