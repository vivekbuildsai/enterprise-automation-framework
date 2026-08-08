from __future__ import annotations

from dataclasses import asdict

import pytest
from cryptography.fernet import InvalidToken

from framework.testdata.builders import SubscriberBuilder
from framework.testdata.masking import DataMasker, TestDataEncryption

pytestmark = pytest.mark.testdata


def test_mask_value_keeps_edges_visible() -> None:
    masked = DataMasker.mask_value("447700900123")
    assert masked.startswith("44")
    assert masked.endswith("23")
    assert "*" in masked
    assert len(masked) == len("447700900123")


def test_mask_value_short_string_fully_masked() -> None:
    assert DataMasker.mask_value("ab") == "**"


def test_mask_record_masks_only_pii_fields() -> None:
    subscriber = asdict(SubscriberBuilder().build())
    masked = DataMasker.mask_record(subscriber)
    assert masked["msisdn"] != subscriber["msisdn"]
    assert masked["subscriber_id"] == subscriber["subscriber_id"]  # not PII, untouched


def test_redact_record_fully_hides_value() -> None:
    subscriber = asdict(SubscriberBuilder().build())
    redacted = DataMasker.redact_record(subscriber, fields={"msisdn"})
    assert redacted["msisdn"] == "***REDACTED***"


def test_encryption_round_trip() -> None:
    key = TestDataEncryption.generate_key()
    ciphertext = TestDataEncryption.encrypt("hunter2", key)
    assert ciphertext != "hunter2"
    assert TestDataEncryption.decrypt(ciphertext, key) == "hunter2"


def test_encryption_wrong_key_fails() -> None:
    key = TestDataEncryption.generate_key()
    wrong_key = TestDataEncryption.generate_key()
    ciphertext = TestDataEncryption.encrypt("hunter2", key)
    with pytest.raises(InvalidToken):
        TestDataEncryption.decrypt(ciphertext, wrong_key)
