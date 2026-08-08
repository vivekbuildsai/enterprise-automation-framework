from __future__ import annotations

from cryptography.fernet import Fernet

from framework.database.utilities.secrets import CredentialResolver


class TestDataEncryption:
    """Thin, TDM-namespaced wrapper over `framework.database.utilities.
    secrets.CredentialResolver`'s Fernet encrypt/decrypt — reused rather
    than reimplemented, since "encrypt a secret value so only ciphertext
    is ever written to disk" is exactly the same problem the database
    layer's `encrypted_password` support already solved. Use this for test
    data (dummy production-like datasets containing values that should
    stay encrypted at rest) rather than live database credentials, which
    should keep going through `CredentialResolver` directly.
    """

    @staticmethod
    def generate_key() -> str:
        return CredentialResolver.generate_key()

    @staticmethod
    def encrypt(plaintext: str, key: str) -> str:
        return CredentialResolver.encrypt(plaintext, key)

    @staticmethod
    def decrypt(ciphertext: str, key: str) -> str:
        return Fernet(key.encode("utf-8")).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
