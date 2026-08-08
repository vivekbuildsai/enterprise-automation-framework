from __future__ import annotations

import pytest

from framework.ai import AIRecommendation, DisabledProvider, RecommendationConfidence
from framework.discovery import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredPage,
    DiscoveryReport,
    recommend_for_report,
)

pytestmark = pytest.mark.discovery


class FakeProvider:
    """Records every prompt it was asked and returns a canned, real
    `AIRecommendation` — proves `recommend_for_report` calls through to
    whatever `AIProvider` it's given without special-casing.
    """

    name = "fake"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        self.prompts.append(prompt)
        return AIRecommendation(
            text="click_submit_button — submits the form",
            confidence=RecommendationConfidence.AI_SUGGESTED,
            provider=self.name,
        )


def _report() -> DiscoveryReport:
    return DiscoveryReport(
        source="test",
        pages=[
            DiscoveredPage(
                url="https://example.test/login",
                title="Login",
                elements=[
                    DiscoveredElement(
                        tag="button",
                        element_type="button",
                        text="Submit",
                        locator=DiscoveredLocator(strategy="test_id", value="submit-btn"),
                    ),
                    DiscoveredElement(
                        tag="input",
                        element_type="input",
                        locator=DiscoveredLocator(strategy="css", value="#username"),
                    ),
                ],
            )
        ],
    )


def test_produces_one_recommendation_per_discovered_element() -> None:
    recommendations = recommend_for_report(_report(), FakeProvider())
    assert len(recommendations) == 2
    assert recommendations[0].page_url == "https://example.test/login"
    assert recommendations[0].element_index == 0
    assert recommendations[1].element_index == 1


def test_recommendation_carries_the_ai_provider_output() -> None:
    recommendations = recommend_for_report(_report(), FakeProvider())
    assert recommendations[0].recommendation.confidence == RecommendationConfidence.AI_SUGGESTED
    assert recommendations[0].recommendation.provider == "fake"


def test_provider_receives_locator_and_text_context() -> None:
    provider = FakeProvider()
    recommend_for_report(_report(), provider)

    assert "submit-btn" in provider.prompts[0]
    assert "test_id" in provider.prompts[0]


def test_discovery_works_without_ai_using_disabled_provider() -> None:
    """Discovery's AI layer is optional — `DisabledProvider` never makes a
    network call, and `recommend_for_report` must still return one
    recommendation per element, each explicitly low-confidence.
    """
    recommendations = recommend_for_report(_report(), DisabledProvider())

    assert len(recommendations) == 2
    assert all(
        r.recommendation.confidence == RecommendationConfidence.DISCOVERED for r in recommendations
    )
    assert all(r.recommendation.provider == "disabled" for r in recommendations)


def test_never_mutates_the_source_report() -> None:
    report = _report()
    original_page_count = len(report.pages)
    original_element_count = len(report.pages[0].elements)

    recommend_for_report(report, FakeProvider())

    assert len(report.pages) == original_page_count
    assert len(report.pages[0].elements) == original_element_count
