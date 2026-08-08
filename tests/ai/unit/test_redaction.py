from __future__ import annotations

import pytest

from framework.ai import redact_secrets

pytestmark = pytest.mark.ai


def test_redacts_password_key_value_pair() -> None:
    result = redact_secrets("connection string: password=SuperSecret123")
    assert "SuperSecret123" not in result
    assert "[REDACTED]" in result


def test_redacts_api_key() -> None:
    result = redact_secrets("api_key: sk-abc123def456")
    assert "sk-abc123def456" not in result


def test_redacts_api_key_written_as_two_words() -> None:
    """Human-readable page text ("API Key: sk-...") uses a space, not an
    underscore — a discovered element's visible text could plausibly say
    exactly this, so the redaction pattern must not require `api_key`/
    `api-key` specifically.
    """
    result = redact_secrets("API Key: sk-abc123def456")
    assert "sk-abc123def456" not in result


def test_redacts_cookie_value() -> None:
    result = redact_secrets("cookie: session=abc123xyz")
    assert "abc123xyz" not in result


def test_redacts_bearer_token() -> None:
    result = redact_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result


def test_leaves_ordinary_text_unchanged() -> None:
    text = "The login button has data-testid='sign-in-btn' and no secrets."
    assert redact_secrets(text) == text
