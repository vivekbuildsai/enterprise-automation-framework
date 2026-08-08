from __future__ import annotations

from pydantic import BaseModel

from framework.ai import AIProvider, AIRecommendation, safe_suggest
from framework.sync.models import RepositoryAnalysis

_MAPPING_PROMPT = (
    "You are helping migrate an existing test-automation repository onto a "
    "Python/Playwright/pytest-based framework. A deterministic scan already "
    "detected the technology below with the given support level and notes. "
    "Suggest one concrete, actionable next step for migrating it — do not "
    "claim certainty beyond what the evidence supports.\n\n"
    "Technology: {name} ({category})\n"
    "Support level: {support_level}\n"
    "Deterministic notes: {notes}\n"
    "Evidence files: {evidence}"
)


class MappingRecommendation(BaseModel):
    """One AI suggestion for one deterministically-detected technology —
    always additive, never a replacement for `DetectedFramework`'s own
    (deterministic) `support_level`/`notes`.
    """

    framework_name: str
    recommendation: AIRecommendation


def recommend_mappings(
    analysis: RepositoryAnalysis, provider: AIProvider
) -> list[MappingRecommendation]:
    """The optional AI layer over repository analysis:

        Repository Analysis -> Framework Discovery Model ->
        Optional AI interpretation -> Mapping Recommendation ->
        Human Review -> Migration Worksheet

    Deterministic analysis (`RepositoryAnalyzer`, `FrameworkAdapter`s)
    remains the source of truth for what was detected and its support
    level — this only adds an optional, separate narrative suggestion per
    detected technology. Works identically whether `provider` is a real
    `AIProvider` or `DisabledProvider`. Never mutates `analysis`, and
    never writes to the analyzed repository or generates code by itself —
    see `generate_migration_worksheet(..., ai_recommendations=...)` for
    how a human-reviewed worksheet can optionally include these.
    """
    recommendations: list[MappingRecommendation] = []
    for framework in analysis.detected_frameworks:
        prompt = _MAPPING_PROMPT.format(
            name=framework.name,
            category=framework.category,
            support_level=framework.support_level.value,
            notes=framework.notes or "(none)",
            evidence=", ".join(framework.evidence) or "(none)",
        )
        suggestion = safe_suggest(
            provider, prompt, context=f"Repository: {analysis.source} ({analysis.primary_language})"
        )
        recommendations.append(
            MappingRecommendation(framework_name=framework.name, recommendation=suggestion)
        )
    return recommendations
