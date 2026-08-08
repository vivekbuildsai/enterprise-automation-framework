from __future__ import annotations

import pytest

from framework.ai import AIRecommendation, DisabledProvider, RecommendationConfidence
from framework.sync import (
    DetectedFramework,
    RepositoryAnalysis,
    SupportLevel,
    generate_migration_worksheet,
    recommend_mappings,
)

pytestmark = pytest.mark.sync


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        self.prompts.append(prompt)
        return AIRecommendation(
            text="Port WebDriver.find_element calls to page.locator() one page at a time.",
            confidence=RecommendationConfidence.AI_SUGGESTED,
            provider=self.name,
        )


def _analysis() -> RepositoryAnalysis:
    return RepositoryAnalysis(
        source="test-repo",
        primary_language="Python",
        detected_frameworks=[
            DetectedFramework(
                name="Selenium",
                category="ui_automation",
                support_level=SupportLevel.PARTIALLY_SUPPORTED,
                evidence=["src/login_page.py"],
                notes="Structural concepts map directly.",
            )
        ],
    )


def test_produces_one_recommendation_per_detected_framework() -> None:
    recommendations = recommend_mappings(_analysis(), FakeProvider())
    assert len(recommendations) == 1
    assert recommendations[0].framework_name == "Selenium"


def test_prompt_includes_deterministic_evidence() -> None:
    provider = FakeProvider()
    recommend_mappings(_analysis(), provider)

    assert "Selenium" in provider.prompts[0]
    assert "partially_supported" in provider.prompts[0]
    assert "src/login_page.py" in provider.prompts[0]


def test_sync_works_without_ai_using_disabled_provider() -> None:
    recommendations = recommend_mappings(_analysis(), DisabledProvider())

    assert len(recommendations) == 1
    assert recommendations[0].recommendation.confidence == RecommendationConfidence.DISCOVERED
    assert recommendations[0].recommendation.provider == "disabled"


def test_never_mutates_the_source_analysis() -> None:
    analysis = _analysis()
    original_count = len(analysis.detected_frameworks)

    recommend_mappings(analysis, FakeProvider())

    assert len(analysis.detected_frameworks) == original_count


class TestWorksheetWithAiRecommendations:
    def test_worksheet_without_recommendations_has_no_ai_section(self) -> None:
        worksheet = generate_migration_worksheet(_analysis())
        assert "AI-suggested mappings" not in worksheet

    def test_worksheet_with_recommendations_includes_a_labeled_section(self) -> None:
        recommendations = recommend_mappings(_analysis(), FakeProvider())
        worksheet = generate_migration_worksheet(_analysis(), ai_recommendations=recommendations)

        assert "AI-suggested mappings (unverified — human review required)" in worksheet
        assert "Selenium" in worksheet
        assert "Port WebDriver.find_element calls" in worksheet

    def test_deterministic_content_is_unaffected_by_ai_recommendations(self) -> None:
        analysis = _analysis()
        without_ai = generate_migration_worksheet(analysis)
        recommendations = recommend_mappings(analysis, FakeProvider())
        with_ai = generate_migration_worksheet(analysis, ai_recommendations=recommendations)

        assert without_ai in with_ai
