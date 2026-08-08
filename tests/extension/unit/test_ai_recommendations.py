"""Optional AI layer over extension gap analysis. Mirrors the same
"works identically whether AI is enabled or disabled" contract
`framework.discovery.ai_recommendations`/`framework.sync.ai_recommendations`
already establish — plus the extension-specific rule this module adds:
only `MANUAL_REVIEW`/`UNKNOWN` items ever get a recommendation.
"""

from __future__ import annotations

import pytest

from framework.ai import AIRecommendation, DisabledProvider, RecommendationConfidence
from framework.extension import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionSubjectType,
    recommend_for_ambiguous_items,
)

pytestmark = pytest.mark.extension


class FakeProvider:
    """Records every prompt it was asked and returns a canned, real
    `AIRecommendation` — proves `recommend_for_ambiguous_items` calls
    through to whatever `AIProvider` it's given without special-casing.
    """

    name = "fake"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        self.prompts.append(prompt)
        return AIRecommendation(
            text="Likely maps to EmployeeApi.get_employee() based on naming similarity.",
            confidence=RecommendationConfidence.AI_SUGGESTED,
            provider=self.name,
        )


def _items() -> list[ExtensionItem]:
    return [
        ExtensionItem(
            subject="GET /employees/42",
            subject_type=ExtensionSubjectType.API_ENDPOINT,
            classification=ExtensionClassification.MANUAL_REVIEW,
            reason="2 existing API capabilities match both endpoint pattern and HTTP method.",
            evidence=["ambiguous"],
        ),
        ExtensionItem(
            subject="Authentication",
            subject_type=ExtensionSubjectType.AUTHENTICATION,
            classification=ExtensionClassification.UNKNOWN,
            reason="No existing authentication mechanism was detected to compare against.",
        ),
        ExtensionItem(
            subject="EmployeeApi.get_employee",
            subject_type=ExtensionSubjectType.API_ENDPOINT,
            classification=ExtensionClassification.REUSE_EXISTING,
            reason="Matches exactly.",
        ),
        ExtensionItem(
            subject="New UI component",
            subject_type=ExtensionSubjectType.UI_COMPONENT,
            classification=ExtensionClassification.CREATE_NEW,
            reason="No existing component matches.",
        ),
    ]


def test_only_manual_review_and_unknown_items_get_a_recommendation() -> None:
    recommendations = recommend_for_ambiguous_items(_items(), FakeProvider())

    subjects = {r.subject for r in recommendations}
    assert subjects == {"GET /employees/42", "Authentication"}


def test_recommendation_carries_the_ai_provider_output() -> None:
    recommendations = recommend_for_ambiguous_items(_items(), FakeProvider())

    assert all(
        r.recommendation.confidence == RecommendationConfidence.AI_SUGGESTED
        for r in recommendations
    )
    assert all(r.recommendation.provider == "fake" for r in recommendations)


def test_provider_receives_subject_and_deterministic_reason_as_context() -> None:
    provider = FakeProvider()
    recommend_for_ambiguous_items(_items(), provider)

    assert any("GET /employees/42" in prompt for prompt in provider.prompts)
    assert any("2 existing API capabilities" in prompt for prompt in provider.prompts)


def test_extension_ai_layer_works_without_ai_using_disabled_provider() -> None:
    """AI assistance here is optional — `DisabledProvider` never makes a
    network call, and ambiguous items must still each get a
    recommendation, explicitly low-confidence.
    """
    recommendations = recommend_for_ambiguous_items(_items(), DisabledProvider())

    assert len(recommendations) == 2
    assert all(
        r.recommendation.confidence == RecommendationConfidence.DISCOVERED for r in recommendations
    )
    assert all(r.recommendation.provider == "disabled" for r in recommendations)


def test_never_mutates_the_source_items() -> None:
    items = _items()
    original_classifications = [item.classification for item in items]

    recommend_for_ambiguous_items(items, FakeProvider())

    assert [item.classification for item in items] == original_classifications


def test_no_ambiguous_items_yields_no_recommendations() -> None:
    clean_items = [
        ExtensionItem(
            subject="EmployeeApi.get_employee",
            subject_type=ExtensionSubjectType.API_ENDPOINT,
            classification=ExtensionClassification.REUSE_EXISTING,
            reason="Matches exactly.",
        )
    ]

    assert recommend_for_ambiguous_items(clean_items, FakeProvider()) == []
