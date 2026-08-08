from __future__ import annotations

import json

import httpx
import pytest

from framework.ai import (
    AIRecommendation,
    DisabledProvider,
    OpenAICompatibleProvider,
    RecommendationConfidence,
    get_provider,
    safe_suggest,
)
from framework.config.models import AIConfig

pytestmark = pytest.mark.ai


class TestDisabledProvider:
    def test_never_makes_a_network_call_and_reports_disabled(self) -> None:
        result = DisabledProvider().suggest("what does this button do?")

        assert isinstance(result, AIRecommendation)
        assert result.confidence == RecommendationConfidence.DISCOVERED
        assert result.provider == "disabled"
        assert "disabled" in result.text.lower()


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestOpenAICompatibleProvider:
    def test_returns_ai_suggested_recommendation_on_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["model"] == "test-model"
            assert body["messages"][0]["role"] == "user"
            return httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [{"message": {"content": "Looks like a login button."}}],
                },
            )

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1",
            model="test-model",
            client=_mock_client(handler),
        )

        result = provider.suggest("what does this button do?")

        assert result.text == "Looks like a login button."
        assert result.confidence == RecommendationConfidence.AI_SUGGESTED
        assert result.provider == "openai_compatible"

    def test_sends_api_key_as_bearer_header(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1",
            model="test-model",
            api_key="secret-key-123",
            client=_mock_client(handler),
        )
        provider.suggest("hello")

        assert captured["auth"] == "Bearer secret-key-123"

    def test_falls_back_gracefully_on_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal error")

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1", model="test-model", client=_mock_client(handler)
        )

        result = provider.suggest("hello")

        assert result.confidence == RecommendationConfidence.DISCOVERED
        assert "unavailable" in result.text.lower()

    def test_falls_back_gracefully_on_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1", model="test-model", client=_mock_client(handler)
        )

        result = provider.suggest("hello")

        assert result.confidence == RecommendationConfidence.DISCOVERED
        assert "unavailable" in result.text.lower()
        assert result.provider == "openai_compatible"

    def test_falls_back_gracefully_on_malformed_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unexpected": "shape"})

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1", model="test-model", client=_mock_client(handler)
        )

        result = provider.suggest("hello")

        assert result.confidence == RecommendationConfidence.DISCOVERED

    def test_redacts_secrets_before_sending(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        provider = OpenAICompatibleProvider(
            endpoint="https://ai.internal/v1", model="test-model", client=_mock_client(handler)
        )
        provider.suggest("the db password=hunter2 is in the config")

        sent_content = captured["body"]["messages"][0]["content"]
        assert "hunter2" not in sent_content


class TestGetProviderFactory:
    def test_returns_disabled_provider_when_not_enabled(self) -> None:
        provider = get_provider(AIConfig(enabled=False))
        assert isinstance(provider, DisabledProvider)

    def test_returns_disabled_provider_when_provider_is_none(self) -> None:
        provider = get_provider(AIConfig(enabled=True, provider="none"))
        assert isinstance(provider, DisabledProvider)

    def test_returns_disabled_provider_when_endpoint_or_model_missing(self) -> None:
        provider = get_provider(AIConfig(enabled=True, provider="openai_compatible", model="x"))
        assert isinstance(provider, DisabledProvider)

    def test_returns_openai_compatible_provider_when_fully_configured(self) -> None:
        provider = get_provider(
            AIConfig(
                enabled=True,
                provider="openai_compatible",
                endpoint="https://ai.internal/v1",
                model="test-model",
            )
        )
        assert isinstance(provider, OpenAICompatibleProvider)


class _MisbehavingProvider:
    """Simulates a third-party `AIProvider` that violates the "never
    raises" contract the built-in providers guarantee.
    """

    name = "misbehaving"

    def suggest(self, prompt: str, *, context: str | None = None) -> AIRecommendation:
        raise RuntimeError("boom — this provider has a bug")


class TestSafeSuggest:
    def test_passes_through_a_well_behaved_providers_result(self) -> None:
        result = safe_suggest(DisabledProvider(), "hello")
        assert result.provider == "disabled"

    def test_a_misbehaving_provider_cannot_crash_the_caller(self) -> None:
        result = safe_suggest(_MisbehavingProvider(), "hello")

        assert result.confidence == RecommendationConfidence.DISCOVERED
        assert result.provider == "misbehaving"
        assert "unavailable" in result.text.lower()
