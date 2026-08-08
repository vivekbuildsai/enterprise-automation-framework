from __future__ import annotations

from typing import Protocol

import httpx

from framework.ai.models import AIRecommendation, RecommendationConfidence
from framework.ai.redaction import redact_secrets
from framework.config.models import AIConfig
from framework.logger import get_logger

_logger = get_logger("AIProvider")

_DISABLED_MESSAGE = (
    "AI assistance is disabled — set ai.enabled=true and configure a provider "
    "(config/environments/*.yaml or AUTOMATION_AI_* env vars) to get real suggestions here."
)
_UNAVAILABLE_MESSAGE = "AI provider unavailable — falling back to deterministic behavior."


class AIProvider(Protocol):
    """Every provider — including the always-available `DisabledProvider`
    — implements this same shape, so callers never need to branch on
    whether AI is actually enabled. AI must be an enhancement layer, not a
    single point of failure: `suggest()` never raises for a
    disabled/unreachable provider, it returns a low-confidence
    recommendation explaining why.
    """

    name: str

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation: ...


class DisabledProvider:
    """The default provider. Always available, never makes a network
    call — returns a clearly-labeled "no AI configured" recommendation
    instead of raising.
    """

    name = "disabled"

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        return AIRecommendation(
            text=_DISABLED_MESSAGE,
            confidence=RecommendationConfidence.DISCOVERED,
            provider=self.name,
        )


class OpenAICompatibleProvider:
    """Works against any endpoint implementing the OpenAI chat-completions
    API shape — cloud OpenAI, Azure OpenAI, and self-hosted/local servers
    that speak the same protocol (Ollama, vLLM, LM Studio, many
    enterprise-hosted inference gateways) without hardcoding a vendor.

    `api_key` is only ever read from configuration (itself only ever
    populated from an environment variable — see `AIConfig`), never
    logged and never included in `AIRecommendation.raw`. The outgoing
    prompt is passed through `redact_secrets()` first.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 30.0,
        temperature: float = 0.2,
        name: str = "openai_compatible",
        client: httpx.Client | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._temperature = temperature
        self.name = name
        # Injectable client — same pattern `framework.api.ApiClient` uses —
        # so tests can pass `httpx.Client(transport=httpx.MockTransport(...))`
        # instead of hitting a real network endpoint.
        self._client = client or httpx.Client()

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        safe_prompt = redact_secrets(prompt)
        content = f"{context}\n\n{safe_prompt}" if context else safe_prompt

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = self._client.post(
                f"{self._endpoint}/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": self._temperature,
                },
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            _logger.warning(
                f"AI provider '{self.name}' unavailable or returned an invalid response: {exc}"
            )
            return AIRecommendation(
                text=_UNAVAILABLE_MESSAGE,
                confidence=RecommendationConfidence.DISCOVERED,
                provider=self.name,
            )

        return AIRecommendation(
            text=text,
            confidence=RecommendationConfidence.AI_SUGGESTED,
            provider=self.name,
            raw={"model": data.get("model", self._model)},
        )


def get_provider(config: AIConfig) -> AIProvider:
    """Factory: the one decision point a caller needs. Returns a working
    `AIProvider` for `settings.ai`, or `DisabledProvider` if AI isn't
    enabled or is misconfigured — every downstream call site treats both
    identically.
    """
    if not config.enabled or config.provider in ("", "none", "disabled"):
        return DisabledProvider()

    if not config.endpoint or not config.model:
        _logger.warning(
            "ai.enabled=true but endpoint/model is missing — falling back to DisabledProvider"
        )
        return DisabledProvider()

    return OpenAICompatibleProvider(
        endpoint=config.endpoint,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
        temperature=config.temperature,
        name=config.provider,
    )


def safe_suggest(
    provider: AIProvider, prompt: str, *, context: str | None = None
) -> AIRecommendation:
    """Calls `provider.suggest()` with one extra safety net on top of
    whatever the provider itself already guarantees: both built-in
    providers (`DisabledProvider`, `OpenAICompatibleProvider`) already
    never raise, but a third-party `AIProvider` implementation could
    violate that contract — a bug, an unhandled exception type, anything.
    Recommendation pipelines (`framework.discovery`/`framework.sync`)
    call through here rather than the provider directly, so one
    misbehaving provider can't crash an otherwise-working discovery/sync
    run — "AI timeout/error cannot break core functionality" holds one
    layer up too, not just inside the provider implementation.
    """
    try:
        return provider.suggest(prompt, context=context)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - deliberately broad: any provider failure must degrade, not propagate
        _logger.warning(f"AI provider '{provider.name}' raised during suggest(): {exc}")
        return AIRecommendation(
            text=_UNAVAILABLE_MESSAGE,
            confidence=RecommendationConfidence.DISCOVERED,
            provider=provider.name,
        )
