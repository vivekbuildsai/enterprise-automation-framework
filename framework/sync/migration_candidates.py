"""Scoped migration-candidate selection — Mode B ("Selective Migration")
from docs/FrameworkSync.md: a customer with hundreds or thousands of
working tests can ask for guidance on just one directory/suite/tag/class/
individual test, leaving everything else completely untouched. Every
candidate carries full provenance back to its exact original source and
is concept-level guidance only — never a claim that conversion happened
(see `MigrationCandidate`'s docstring).
"""

from __future__ import annotations

from framework.exceptions import ConfigurationError
from framework.sync.cross_language_mapping import lookup_cross_language_mappings
from framework.sync.models import (
    CrossLanguageMapping,
    MappingStatus,
    MigrationCandidate,
    MigrationScope,
    RepositoryAnalysis,
    RiskLevel,
    Test,
)

# A test whose *own* technology is already this framework's stack has
# nothing to migrate — never routed through the cross-language mapping
# table (which only maps *other* technologies onto this one).
_ALREADY_THIS_STACK = {"pytest", "Playwright"}

_STATUS_TO_RISK: dict[MappingStatus, RiskLevel] = {
    MappingStatus.DIRECTLY_REUSABLE: RiskLevel.LOW,
    MappingStatus.CONCEPTUALLY_MAPPABLE: RiskLevel.MEDIUM,
    MappingStatus.REQUIRES_ADAPTATION: RiskLevel.HIGH,
    MappingStatus.NOT_DETECTED: RiskLevel.UNKNOWN,
    MappingStatus.UNSUPPORTED: RiskLevel.UNKNOWN,
    MappingStatus.UNKNOWN: RiskLevel.UNKNOWN,
}


def _filter_tests(tests: list[Test], scope: MigrationScope, selector: str | None) -> list[Test]:
    if scope == MigrationScope.REPOSITORY:
        return list(tests)

    if not selector:
        raise ConfigurationError(f"Migration scope {scope.value!r} requires a --selector value.")

    if scope == MigrationScope.DIRECTORY:
        prefix = selector.rstrip("/") + "/"
        return [t for t in tests if t.source_file.startswith(prefix)]
    if scope == MigrationScope.SUITE:
        return [t for t in tests if t.source_file == selector]
    if scope == MigrationScope.TAG:
        return [t for t in tests if selector.lower() in (tag.lower() for tag in t.tags)]
    if scope == MigrationScope.CLASS:
        return [t for t in tests if t.class_name == selector]
    if scope == MigrationScope.TEST:
        return [t for t in tests if selector in (t.identifier, t.name)]

    raise ConfigurationError(f"Unknown migration scope: {scope.value!r}")  # pragma: no cover


def _index_by_source(
    mappings: list[CrossLanguageMapping],
) -> dict[str, list[CrossLanguageMapping]]:
    index: dict[str, list[CrossLanguageMapping]] = {}
    for mapping in mappings:
        index.setdefault(mapping.source_technology, []).append(mapping)
    return index


def _technology_label(analysis: RepositoryAnalysis, test: Test) -> str:
    ui_technology = next(
        (f.name for f in analysis.detected_frameworks if f.category == "ui_automation"), None
    )
    parts = [p for p in (analysis.primary_language, ui_technology, test.technology) if p]
    deduplicated = list(dict.fromkeys(p for p in parts if p != "unknown"))
    return " / ".join(deduplicated) if deduplicated else test.technology


def _guidance_for(
    test: Test, mappings_by_source: dict[str, list[CrossLanguageMapping]]
) -> tuple[str, MappingStatus, str]:
    """`(target_technology, status, reason)` — never "converted
    successfully": `status` is always concept-level guidance, `reason`
    always explains why, never asserts an actual conversion took place.
    """
    if test.technology in _ALREADY_THIS_STACK:
        return (
            test.technology,
            MappingStatus.DIRECTLY_REUSABLE,
            "Already this framework's own stack — no migration needed.",
        )

    if hits := mappings_by_source.get(test.technology):
        mapping = hits[0]
        return mapping.target_technology, mapping.status, mapping.manual_action

    return (
        "(not yet determined)",
        MappingStatus.UNKNOWN,
        f"No migration guidance is available yet for {test.technology!r} — manual review required.",
    )


def select_migration_candidates(
    analysis: RepositoryAnalysis,
    *,
    scope: MigrationScope = MigrationScope.REPOSITORY,
    selector: str | None = None,
) -> list[MigrationCandidate]:
    """Selects the subset of `analysis.tests` matching `scope`/`selector`
    and produces one `MigrationCandidate` per selected test — the rest of
    the repository's tests are never touched, listed, or implied to need
    any action (Mode A, "Preserve," is the default: `scope=repository`
    still only *analyzes*, it never migrates anything by itself).
    """
    selected = _filter_tests(analysis.tests, scope, selector)
    mappings_by_source = _index_by_source(lookup_cross_language_mappings(analysis))

    candidates: list[MigrationCandidate] = []
    for test in selected:
        target, status, reason = _guidance_for(test, mappings_by_source)
        candidates.append(
            MigrationCandidate(
                test=test,
                technology=_technology_label(analysis, test),
                target_technology=target,
                status=status,
                risk=_STATUS_TO_RISK[status],
                reason=reason,
            )
        )
    return candidates
