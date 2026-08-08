from __future__ import annotations

from framework.sync.ai_recommendations import MappingRecommendation
from framework.sync.cross_language_mapping import lookup_cross_language_mappings
from framework.sync.migration_candidates import select_migration_candidates
from framework.sync.models import (
    ExecutionModel,
    MigrationCandidate,
    MigrationScope,
    RepositoryAnalysis,
    RobotStructure,
)
from framework.sync.test_inventory import format_inventory

_WORKSHEET_HEADER = "# Migration Worksheet — GENERATED, REVIEW BEFORE ACTING\n\n"

_NO_FRAMEWORK_NOTE = "_No migration notes available._"

_MAX_MIGRATION_CANDIDATES_SHOWN = 50


def _inventory_lines(analysis: RepositoryAnalysis) -> list[str]:
    ui_framework = next(
        (f.name for f in analysis.detected_frameworks if f.category == "ui_automation"), None
    )
    execution_model = analysis.execution_model
    rendered = format_inventory(
        analysis.inventory,
        language=analysis.primary_language,
        ui_framework=ui_framework,
        runner=execution_model.runner if execution_model else None,
        primary_execution=execution_model.command if execution_model else None,
        parallelism=execution_model.parallelism if execution_model else None,
    )
    return ["```", rendered, "```", ""]


def _execution_model_lines(execution_model: ExecutionModel) -> list[str]:
    lines = ["## Execution model\n", "Captured for understanding — never executed by this tool.\n"]
    rows = [
        ("Command", execution_model.command),
        ("Runner", execution_model.runner),
        ("Parallelism", execution_model.parallelism),
        ("Retries", execution_model.retries),
        ("Browser", execution_model.browser),
        ("Environments", ", ".join(execution_model.environments) or None),
        ("Reporting", ", ".join(execution_model.reporting) or None),
        ("Test selection", execution_model.test_selection),
    ]
    for label, value in rows:
        if value is not None:
            lines.append(f"- {label}: {value}")
    lines.append("")
    return lines


def _language_lines(analysis: RepositoryAnalysis) -> list[str]:
    lines = [f"Primary language: **{analysis.primary_language}**"]
    if len(analysis.language_breakdown) > 1:
        # A mixed-language repository is never collapsed to just its
        # primary language in the worksheet — every detected language and
        # its file count is listed, so e.g. a Java-primary repo with a
        # Python test-data layer is visible, not hidden.
        secondary = sorted(
            (lang, count)
            for lang, count in analysis.language_breakdown.items()
            if lang != analysis.primary_language
        )
        lines.append(
            "Also detected: " + ", ".join(f"{lang} ({count} files)" for lang, count in secondary)
        )
    lines.append("")
    return lines


def _detected_framework_lines(analysis: RepositoryAnalysis) -> list[str]:
    lines = ["## Detected frameworks/technologies\n"]
    if not analysis.detected_frameworks:
        lines.append("- None detected — this repository needs manual classification.\n")
    for framework in analysis.detected_frameworks:
        lines.append(f"### {framework.name} ({framework.support_level.value})")
        lines.append(framework.notes or _NO_FRAMEWORK_NOTE)
        if framework.evidence:
            lines.append("Evidence: " + ", ".join(f"`{e}`" for e in framework.evidence))
        lines.append("")
    return lines


def _robot_structure_lines(robot: RobotStructure) -> list[str]:
    lines = [
        "## Robot Framework structure\n",
        f"- {robot.test_case_count} Test Case(s), {robot.keyword_count} user Keyword(s), "
        f"{robot.resource_file_count} Resource file(s), {robot.variable_count} Variable(s)",
    ]
    if robot.library_names:
        lines.append("- Libraries: " + ", ".join(f"`{lib}`" for lib in robot.library_names))
    lifecycle = [
        label
        for label, present in (
            ("Suite Setup", robot.has_suite_setup),
            ("Suite Teardown", robot.has_suite_teardown),
            ("Test Setup", robot.has_test_setup),
            ("Test Teardown", robot.has_test_teardown),
        )
        if present
    ]
    if lifecycle:
        lines.append("- Lifecycle hooks: " + ", ".join(lifecycle))
    lines.append("")
    return lines


def _cross_language_mapping_lines(analysis: RepositoryAnalysis) -> list[str]:
    mappings = lookup_cross_language_mappings(analysis)
    if not mappings:
        return []
    lines = [
        "## Cross-language mapping\n",
        "Concept-level guidance only — never automatic conversion. Review each "
        "manual action before acting on it.\n",
    ]
    for mapping in mappings:
        lines.append(f"### {mapping.source_technology} — {mapping.concept}")
        lines.append(f"- Target: {mapping.target_technology}")
        lines.append(f"- Status: {mapping.status.value}")
        lines.append(f"- Manual action: {mapping.manual_action}")
        lines.append("")
    return lines


def _migration_candidate_lines(
    candidates: list[MigrationCandidate], scope: MigrationScope, selector: str | None
) -> list[str]:
    if not candidates:
        return []

    scope_note = f" (scope: {scope.value}" + (f" = {selector!r})" if selector else ")")
    lines = [
        f"## Migration candidates{scope_note}\n",
        "Per-test provenance and concept-level guidance only — **never** a claim that "
        "conversion happened. The remaining tests not listed here are untouched and "
        "require no action.\n",
    ]
    shown = candidates[:_MAX_MIGRATION_CANDIDATES_SHOWN]
    for candidate in shown:
        lines.append(f"### {candidate.test.source_file} — {candidate.test.name}")
        lines.append(f"- Source: `{candidate.test.identifier}`")
        lines.append(f"- Technology: {candidate.technology}")
        lines.append(f"- Target: {candidate.target_technology}")
        lines.append(f"- Mapping: {candidate.status.value}")
        lines.append(f"- Risk: {candidate.risk.value}")
        lines.append(f"- Reason: {candidate.reason}")
        lines.append("")
    if len(candidates) > len(shown):
        lines.append(f"- ...and {len(candidates) - len(shown)} more (see the full report JSON).")
    return lines


def _structure_summary_lines(analysis: RepositoryAnalysis) -> list[str]:
    structure = analysis.structure
    lines = [
        "## Structure summary\n",
        f"- {structure.total_files} files, {structure.test_files} look like tests, "
        f"{structure.page_object_like_files} look like Page Objects",
        f"- Docker: {'yes' if structure.has_docker else 'no'}, "
        f"CI: {'yes' if structure.has_ci else 'no'}",
    ]
    if structure.dependency_files:
        lines.append(
            "- Dependency files: " + ", ".join(f"`{f}`" for f in structure.dependency_files)
        )
    lines.append("")
    return lines


def _finding_lines(analysis: RepositoryAnalysis) -> list[str]:
    if not analysis.findings:
        return []
    shown = analysis.findings[:50]
    lines = [f"## {len(analysis.findings)} finding(s) to review before migrating\n"]
    for finding in shown:
        location = f"{finding.file}:{finding.line}" if finding.line else finding.file
        lines.append(f"- **{finding.category}** — `{location}` — {finding.description}")
    if len(analysis.findings) > len(shown):
        lines.append(
            f"- ...and {len(analysis.findings) - len(shown)} more (see the full report JSON)."
        )
    return lines


def _ai_recommendation_lines(ai_recommendations: list[MappingRecommendation]) -> list[str]:
    if not ai_recommendations:
        return []
    lines = ["", "## AI-suggested mappings (unverified — human review required)\n"]
    for item in ai_recommendations:
        rec = item.recommendation
        lines.append(f"### {item.framework_name} — via `{rec.provider}` ({rec.confidence.value})")
        lines.append(rec.text)
        lines.append("")
    return lines


def generate_migration_worksheet(
    analysis: RepositoryAnalysis,
    *,
    ai_recommendations: list[MappingRecommendation] | None = None,
    migration_scope: MigrationScope = MigrationScope.REPOSITORY,
    migration_selector: str | None = None,
) -> str:
    """Sync Mode 2 (SCAFFOLD): a human-readable starting point for a
    migration — never source code transformation. Lists what was
    detected and the concrete next step for each, so a human can plan the
    actual porting work themselves.

    `migration_scope`/`migration_selector` implement Mode B ("Selective
    Migration" — see docs/FrameworkSync.md): the default,
    `MigrationScope.REPOSITORY`, still only *analyzes* every detected
    test, never migrates anything by itself; a narrower scope (directory/
    suite/tag/class/test) restricts the "Migration candidates" section to
    exactly that subset, leaving every other test unmentioned and
    untouched.

    `ai_recommendations` is entirely optional — omit it (the default) for
    a purely deterministic worksheet. When provided (see
    `framework.sync.ai_recommendations.recommend_mappings`), each
    suggestion is appended in its own clearly-labeled, unverified section
    — deterministic analysis stays the primary content either way.

    Mode 3 (MIGRATE — generating translated source) and Mode 4 (SYNC —
    diff-driven re-application against an existing target) are
    intentionally not implemented; see `SyncMode` and
    docs/FrameworkSync.md for why.
    """
    lines = [_WORKSHEET_HEADER, f"Source: `{analysis.source}`", f"Analyzed: {analysis.analyzed_at}"]
    lines.extend(_language_lines(analysis))
    lines.extend(_inventory_lines(analysis))
    lines.extend(_detected_framework_lines(analysis))
    if analysis.robot_structure is not None:
        lines.extend(_robot_structure_lines(analysis.robot_structure))
    lines.extend(_cross_language_mapping_lines(analysis))
    if analysis.execution_model is not None:
        lines.extend(_execution_model_lines(analysis.execution_model))
    if analysis.tests:
        candidates = select_migration_candidates(
            analysis, scope=migration_scope, selector=migration_selector
        )
        lines.extend(_migration_candidate_lines(candidates, migration_scope, migration_selector))
    lines.extend(_structure_summary_lines(analysis))
    lines.extend(_finding_lines(analysis))
    lines.extend(_ai_recommendation_lines(ai_recommendations or []))

    return "\n".join(lines)
