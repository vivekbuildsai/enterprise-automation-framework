from __future__ import annotations

from pydantic import BaseModel

from framework.ai import AIProvider, AIRecommendation, safe_suggest
from framework.discovery.models import DiscoveryReport

_ELEMENT_PROMPT = (
    "You are reviewing one interactive element discovered on a web page during "
    "test-automation onboarding. Suggest a short, business-action-style method name "
    "for it (e.g. 'click_submit_button', 'fill_username_field') and one sentence on "
    "what it likely does. Do not invent behavior beyond what's given.\n\n"
    "Tag: {tag}\nVisible text: {text!r}\nLocator: {strategy}={value}"
)


class ElementRecommendation(BaseModel):
    """One AI suggestion for one discovered element — always additive,
    never a replacement for the element's own (deterministically
    discovered) locator/text. Pairs with the source element by index so a
    human reviewer can match a recommendation back to
    `DiscoveredPage.elements[element_index]` before acting on it.
    """

    page_url: str
    element_index: int
    element_summary: str
    recommendation: AIRecommendation


def recommend_for_report(
    report: DiscoveryReport, provider: AIProvider
) -> list[ElementRecommendation]:
    """The optional AI layer over discovery output:

        Discovery -> Discovery Model -> Optional AI Provider ->
        Recommendation -> RecommendationConfidence -> Human Review ->
        Approved Discovery Model

    Never mutates `report` — deterministic discovery (`UIDiscoveryEngine`)
    stays the source of truth for every locator/element; this only adds a
    separate, inspectable list of suggestions a human can choose to act
    on. Works identically whether `provider` is a real `AIProvider` or
    `DisabledProvider` — every element gets a recommendation either way,
    just with `RecommendationConfidence.DISCOVERED` (i.e. "no AI opinion
    available") instead of `AI_SUGGESTED` when AI isn't configured.
    "Approving" a recommendation is a human action (e.g. renaming a
    generated Page Object method) — nothing here writes to source code.
    """
    recommendations: list[ElementRecommendation] = []
    for page in report.pages:
        for index, element in enumerate(page.elements):
            prompt = _ELEMENT_PROMPT.format(
                tag=element.tag,
                text=element.text,
                strategy=element.locator.strategy,
                value=element.locator.value,
            )
            suggestion = safe_suggest(provider, prompt, context=f"Page: {page.url} ({page.title})")
            recommendations.append(
                ElementRecommendation(
                    page_url=page.url,
                    element_index=index,
                    element_summary=f"<{element.tag}> {element.text or element.locator.value}",
                    recommendation=suggestion,
                )
            )
    return recommendations
