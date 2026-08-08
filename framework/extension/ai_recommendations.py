"""Optional AI layer over extension gap analysis — reuses
`framework.ai` exactly the way `framework.sync.ai_recommendations` and
`framework.discovery.ai_recommendations` already do, so this never
re-implements provider selection, redaction, or the "AI must degrade,
never break core functionality" contract a third time.

The governing rule this module follows literally: "AI may assist
ambiguous mappings" — not "AI comments on everything." A recommendation
is only ever generated for an `ExtensionItem` the deterministic
correlation (`framework.extension.correlation`) could not confidently
resolve on its own (`MANUAL_REVIEW`/`UNKNOWN`); an item already classified
`REUSE_EXISTING`/`EXTEND_EXISTING`/`CREATE_NEW` has nothing ambiguous left
for AI to weigh in on, and is skipped.
"""

from __future__ import annotations

from pydantic import BaseModel

from framework.ai import AIProvider, AIRecommendation, safe_suggest
from framework.extension.models import ExtensionClassification, ExtensionItem

_MAPPING_PROMPT = (
    "You are helping a customer extend their existing, mature test-automation "
    "framework to cover a brand-new UI that has zero automation today. A "
    "deterministic comparison against the existing framework's capability "
    "catalog could not confidently classify the item below. Suggest which "
    "existing capability (if any) it most likely maps to, or confirm it "
    "genuinely needs to be created new. Do not claim certainty beyond what "
    "the evidence supports.\n\n"
    "Subject: {subject} ({subject_type})\n"
    "Deterministic classification: {classification}\n"
    "Deterministic reason: {reason}\n"
    "Evidence so far: {evidence}"
)


class ExtensionMappingRecommendation(BaseModel):
    """One AI suggestion for one ambiguous `ExtensionItem` — always
    additive, never a replacement for the deterministic classification
    that triggered it. Pairs with the source item by `subject` so a human
    reviewer can match a recommendation back to the extension report
    before acting on it; nothing here changes `item.classification`.
    """

    subject: str
    recommendation: AIRecommendation


def recommend_for_ambiguous_items(
    items: list[ExtensionItem], provider: AIProvider
) -> list[ExtensionMappingRecommendation]:
    """The optional AI layer over extension gap analysis:

        Extension Gap Analysis -> MANUAL_REVIEW/UNKNOWN items ->
        Optional AI Provider -> ExtensionMappingRecommendation ->
        Human Review

    Never mutates `items` and never changes a classification by itself —
    deterministic correlation (`framework.extension.correlation`) remains
    the source of truth for every REUSE_EXISTING/EXTEND_EXISTING/
    CREATE_NEW verdict; this only adds a separate, inspectable suggestion
    for the subset the deterministic pass couldn't resolve. Works
    identically whether `provider` is a real `AIProvider` or
    `DisabledProvider` — every ambiguous item gets a recommendation either
    way, just with `RecommendationConfidence.DISCOVERED` (i.e. "no AI
    opinion available") instead of `AI_SUGGESTED` when AI isn't
    configured.
    """
    recommendations: list[ExtensionMappingRecommendation] = []
    for item in items:
        if item.classification not in (
            ExtensionClassification.MANUAL_REVIEW,
            ExtensionClassification.UNKNOWN,
        ):
            continue
        prompt = _MAPPING_PROMPT.format(
            subject=item.subject,
            subject_type=item.subject_type.value,
            classification=item.classification.value,
            reason=item.reason,
            evidence=", ".join(item.evidence) or "(none)",
        )
        suggestion = safe_suggest(
            provider, prompt, context=f"Subject type: {item.subject_type.value}"
        )
        recommendations.append(
            ExtensionMappingRecommendation(subject=item.subject, recommendation=suggestion)
        )
    return recommendations
