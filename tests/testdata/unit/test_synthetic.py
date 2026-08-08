from __future__ import annotations

from dataclasses import asdict

import pytest

from framework.testdata.builders import SubscriberBuilder
from framework.testdata.synthetic import Anonymizer, SyntheticDatasetGenerator

pytestmark = pytest.mark.testdata


def test_generate_bulk_produces_distinct_records() -> None:
    records = SyntheticDatasetGenerator.generate(SubscriberBuilder().gold_tier(), 10)
    assert len(records) == 10
    assert len({r.subscriber_id for r in records}) == 10
    assert all(r.cos == "Gold" for r in records)


def test_generate_with_variation_uses_fresh_builder_per_record() -> None:
    records = SyntheticDatasetGenerator.generate_with_variation(
        lambda: SubscriberBuilder().blocked(), 4
    )
    assert len(records) == 4
    assert all(r.status == "BLOCKED" for r in records)


def test_anonymizer_replaces_pii_fields() -> None:
    subscriber = asdict(SubscriberBuilder().build())
    anonymized = Anonymizer.anonymize(subscriber, fields={"msisdn", "imsi"})
    assert anonymized["msisdn"] != subscriber["msisdn"]
    assert anonymized["imsi"] != subscriber["imsi"]
    assert anonymized["subscriber_id"] == subscriber["subscriber_id"]


def test_anonymizer_leaves_non_pii_and_unmapped_fields_untouched() -> None:
    record = {"status": "ACTIVE", "cos": "Gold"}
    anonymized = Anonymizer.anonymize(record, fields={"status", "cos"})
    assert anonymized == record  # neither field has a registered generator
