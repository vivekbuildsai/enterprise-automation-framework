from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from framework.config.models import DatabaseConfig
from framework.database.exceptions import DatabaseConnectionError

_SECRET_KEY_ENV_VAR = (
    "AUTOMATION_DB_SECRET_KEY"  # nosec B105 - env var *name*, not a credential value
)


class CredentialResolver:
    """Resolves the real password for a `DatabaseConfig` without ever
    printing, logging, or otherwise exposing it.

    Two supported sources, in priority order:
      1. `config.encrypted_password` — Fernet ciphertext, decrypted with the
         key in the `AUTOMATION_DB_SECRET_KEY` environment variable. This is what
         lets a ciphertext (not a plaintext secret) live in a committed YAML
         file.
      2. `config.password` — already resolved from `${AUTOMATION_DB_PASSWORD}` (or
         similar) by `framework.config.settings`'s `${VAR}` substitution, so
         the plaintext itself still only ever lives in the environment/`.env`,
         never in a tracked file.

    Neither path logs the resolved value — callers must not log it either.
    """

    @staticmethod
    def resolve_password(config: DatabaseConfig) -> str:
        if config.encrypted_password:
            return CredentialResolver._decrypt(config.encrypted_password)
        return config.password

    @staticmethod
    def _decrypt(ciphertext: str) -> str:
        key = os.environ.get(_SECRET_KEY_ENV_VAR)
        if not key:
            raise DatabaseConnectionError(
                f"Database config supplies an encrypted_password but {_SECRET_KEY_ENV_VAR} "
                "is not set in the environment — cannot decrypt credentials."
            )
        try:
            return Fernet(key.encode("utf-8")).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise DatabaseConnectionError(
                f"Failed to decrypt database credentials with {_SECRET_KEY_ENV_VAR} — "
                "wrong key or corrupted ciphertext."
            ) from exc

    @staticmethod
    def encrypt(plaintext: str, key: str) -> str:
        """One-off helper for generating `encrypted_password` values to put
        in YAML (e.g. `python -c "from framework.database.utilities.secrets
        import CredentialResolver as C; print(C.encrypt('secret', 'key'))"`).
        Not used by the framework at runtime — only by whoever is authoring
        the encrypted config value.
        """
        return Fernet(key.encode("utf-8")).encrypt(plaintext.encode("utf-8")).decode("utf-8")

    @staticmethod
    def generate_key() -> str:
        """Generates a new Fernet key for `AUTOMATION_DB_SECRET_KEY`."""
        return Fernet.generate_key().decode("utf-8")
