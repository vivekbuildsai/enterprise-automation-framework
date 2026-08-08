from __future__ import annotations

from framework.sync.ai_recommendations import MappingRecommendation
from framework.sync.models import RepositoryAnalysis

_WORKSHEET_HEADER = "# Migration Worksheet — GENERATED, REVIEW BEFORE ACTING\n\n"

_NO_FRAMEWORK_NOTE = "_No migration notes available._"


def generate_migration_worksheet(
    analysis: RepositoryAnalysis,
    *,
    ai_recommendations: list[MappingRecommendation] | None = None,
) -> str:
    """Sync Mode 2 (SCAFFOLD): a human-readable starting point for a
    migration — never source code transformation. Lists what was
    detected and the concrete next step for each, so a human can plan the
    actual porting work themselves.

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
    lines.append(f"Primary language: **{analysis.primary_language}**\n")

    lines.append("## Detected frameworks/technologies\n")
    if not analysis.detected_frameworks:
        lines.append("- None detected — this repository needs manual classification.\n")
    for framework in analysis.detected_frameworks:
        lines.append(f"### {framework.name} ({framework.support_level.value})")
        lines.append(framework.notes or _NO_FRAMEWORK_NOTE)
        if framework.evidence:
            lines.append("Evidence: " + ", ".join(f"`{e}`" for e in framework.evidence))
        lines.append("")

    lines.append("## Structure summary\n")
    structure = analysis.structure
    lines.append(
        f"- {structure.total_files} files, {structure.test_files} look like tests, "
        f"{structure.page_object_like_files} look like Page Objects"
    )
    lines.append(
        f"- Docker: {'yes' if structure.has_docker else 'no'}, "
        f"CI: {'yes' if structure.has_ci else 'no'}"
    )
    if structure.dependency_files:
        lines.append(
            "- Dependency files: " + ", ".join(f"`{f}`" for f in structure.dependency_files)
        )
    lines.append("")

    if analysis.findings:
        shown = analysis.findings[:50]
        lines.append(f"## {len(analysis.findings)} finding(s) to review before migrating\n")
        for finding in shown:
            location = f"{finding.file}:{finding.line}" if finding.line else finding.file
            lines.append(f"- **{finding.category}** — `{location}` — {finding.description}")
        if len(analysis.findings) > len(shown):
            lines.append(
                f"- ...and {len(analysis.findings) - len(shown)} more (see the full report JSON)."
            )

    if ai_recommendations:
        lines.append("")
        lines.append("## AI-suggested mappings (unverified — human review required)\n")
        for item in ai_recommendations:
            rec = item.recommendation
            lines.append(
                f"### {item.framework_name} — via `{rec.provider}` ({rec.confidence.value})"
            )
            lines.append(rec.text)
            lines.append("")

    return "\n".join(lines)
