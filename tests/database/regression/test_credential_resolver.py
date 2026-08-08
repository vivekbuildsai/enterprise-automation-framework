from __future__ import annotations

import pytest

from framework.config.models import DatabaseConfig
from framework.database.exceptions import DatabaseConnectionError
from framework.database.utilities.secrets import CredentialResolver

pytestmark = [pytest.mark.regression, pytest.mark.database]


def test_resolve_password_falls_back_to_plain_password() -> None:
    config = DatabaseConfig(dialect="sqlite", password="plain-text-secret")
    assert CredentialResolver.resolve_password(config) == "plain-text-secret"


def test_encrypt_decrypt_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    key = CredentialResolver.generate_key()
    ciphertext = CredentialResolver.encrypt("hunter2", key)
    monkeypatch.setenv("AUTOMATION_DB_SECRET_KEY", key)

    config = DatabaseConfig(dialect="sqlite", encrypted_password=ciphertext)
    assert CredentialResolver.resolve_password(config) == "hunter2"


def test_encrypted_password_takes_priority_over_plain_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = CredentialResolver.generate_key()
    ciphertext = CredentialResolver.encrypt("from-ciphertext", key)
    monkeypatch.setenv("AUTOMATION_DB_SECRET_KEY", key)

    config = DatabaseConfig(
        dialect="sqlite", password="from-plaintext", encrypted_password=ciphertext
    )
    assert CredentialResolver.resolve_password(config) == "from-ciphertext"


def test_missing_secret_key_raises_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOMATION_DB_SECRET_KEY", raising=False)
    config = DatabaseConfig(dialect="sqlite", encrypted_password="does-not-matter")

    with pytest.raises(DatabaseConnectionError, match="AUTOMATION_DB_SECRET_KEY"):
        CredentialResolver.resolve_password(config)


def test_wrong_secret_key_raises_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    ciphertext = CredentialResolver.encrypt("secret", CredentialResolver.generate_key())
    monkeypatch.setenv(
        "AUTOMATION_DB_SECRET_KEY", CredentialResolver.generate_key()
    )  # different key
    config = DatabaseConfig(dialect="sqlite", encrypted_password=ciphertext)

    with pytest.raises(DatabaseConnectionError, match="decrypt"):
        CredentialResolver.resolve_password(config)
