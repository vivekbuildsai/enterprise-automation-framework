"""Example E — Optional AI Assistance.

Demonstrates AI as an optional recommendation layer over Discovery output:

    discovery (DiscoveryReport)
          |
    AI suggestion         (AIProvider.suggest() via recommend_for_report())
          |
    confidence             (RecommendationConfidence — never presented as fact)
          |
    human review            (a plain JSON/inspectable list — nothing is
                              auto-applied to the DiscoveryReport or to
                              any generated code)

AI is never required: `test_discovery_recommendations_work_without_ai`
runs with the framework's default `DisabledProvider` — no configuration,
no network call, no API key. `test_discovery_recommendations_with_a_configured_ai_provider`
shows what a *real* provider's response would add, using a mocked HTTP
transport (same pattern `tests/ai/` uses) — still entirely local, no real
AI service or API key involved.

Run:
    poetry run pytest examples/ai_assistance -v
"""

from __future__ import annotations

import httpx

from framework.ai import DisabledProvider, OpenAICompatibleProvider, RecommendationConfidence
from framework.discovery import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredPage,
    DiscoveryReport,
    recommend_for_report,
)


def _sample_report() -> DiscoveryReport:
    return DiscoveryReport(
        source="example",
        pages=[
            DiscoveredPage(
                url="https://example.test/login",
                title="Login",
                elements=[
                    DiscoveredElement(
                        tag="button",
                        element_type="button",
                        text="Sign In",
                        locator=DiscoveredLocator(strategy="test_id", value="submit-login"),
                    )
                ],
            )
        ],
    )


def test_discovery_recommendations_work_without_ai() -> None:
    """The default, always-available path — no `ai.enabled`, no network
    call, no API key. Discovery is fully usable with AI entirely absent.
    """
    report = _sample_report()

    recommendations = recommend_for_report(report, DisabledProvider())

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.recommendation.confidence == RecommendationConfidence.DISCOVERED
    assert recommendation.recommendation.provider == "disabled"
    # The underlying DiscoveryReport is never touched — this is purely an
    # additive, separate artifact for a human to read.
    assert report.pages[0].elements[0].locator.value == "submit-login"


def test_discovery_recommendations_with_a_configured_ai_provider() -> None:
    """What a *real* AI provider's response looks like — mocked here so
    the example runs without a real AI service or API key, using the same
    `httpx.MockTransport` pattern `tests/ai/unit/test_providers.py` uses.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "example-model",
                "choices": [
                    {"message": {"content": "click_sign_in_button — submits the login form"}}
                ],
            },
        )

    provider = OpenAICompatibleProvider(
        endpoint="https://ai.internal/v1",
        model="example-model",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    report = _sample_report()

    recommendations = recommend_for_report(report, provider)

    recommendation = recommendations[0]
    assert recommendation.recommendation.confidence == RecommendationConfidence.AI_SUGGESTED
    assert "click_sign_in_button" in recommendation.recommendation.text

    # Human review: a real workflow would read this list, decide which
    # suggestions to act on, and rename the generated Page Object method
    # itself — nothing here writes back to the DiscoveryReport or to any
    # generated code automatically.
    assert recommendation.recommendation.confidence != RecommendationConfidence.MANUALLY_CONFIRMED
