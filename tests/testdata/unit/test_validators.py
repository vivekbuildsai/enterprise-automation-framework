from __future__ import annotations

from dataclasses import asdict

import pytest

from framework.testdata.builders import SteeringRuleBuilder, SubscriberBuilder, TenantBuilder
from framework.testdata.generators import TelecomIdentifierGenerator
from framework.testdata.validators import (
    BusinessRuleValidator,
    FormatValidator,
    RelationshipValidator,
    SchemaValidator,
    UniquenessValidator,
    ValidationResult,
    business_rules,
)

pytestmark = pytest.mark.testdata


class TestFormatValidator:
    def test_valid_email(self) -> None:
        assert FormatValidator.is_valid_email("a@b.com").valid

    def test_invalid_email(self) -> None:
        assert not FormatValidator.is_valid_email("not-an-email").valid

    def test_valid_imei(self) -> None:
        assert FormatValidator.is_valid_imei(TelecomIdentifierGenerator.imei()).valid

    def test_invalid_imei(self) -> None:
        assert not FormatValidator.is_valid_imei("12345").valid

    def test_valid_iccid(self) -> None:
        assert FormatValidator.is_valid_iccid(TelecomIdentifierGenerator.iccid()).valid

    def test_valid_imsi(self) -> None:
        assert FormatValidator.is_valid_imsi(TelecomIdentifierGenerator.imsi()).valid

    def test_valid_msisdn(self) -> None:
        assert FormatValidator.is_valid_msisdn(TelecomIdentifierGenerator.msisdn()).valid


class TestBusinessRuleValidator:
    def test_registered_default_rules_pass_for_valid_subscriber(self) -> None:
        subscriber = SubscriberBuilder().gold_tier().build()
        result = business_rules.validate(asdict(subscriber))
        assert result.valid

    def test_cos_rule_rejects_invalid_tier(self) -> None:
        record = {"cos": "Platinum"}
        result = business_rules.validate(record, rule_names=["cos_is_valid_tier"])
        assert not result.valid

    def test_steering_flags_mutually_exclusive_rule(self) -> None:
        zone = SteeringRuleBuilder().with_leakage().with_anti_sor().build()
        result = business_rules.validate(asdict(zone))
        assert not result.valid
        assert "leakage_flag" in result.errors[0]

    def test_amount_non_negative_rule(self) -> None:
        result = business_rules.validate({"amount": -5}, rule_names=["amount_is_non_negative"])
        assert not result.valid

    def test_custom_rule_registration(self) -> None:
        validator = BusinessRuleValidator()
        validator.register("always_fail", lambda record: ValidationResult.fail("nope"))
        result = validator.validate({})
        assert not result.valid


class TestUniquenessValidator:
    def test_within_batch_detects_duplicates(self) -> None:
        records = [{"id": "1"}, {"id": "2"}, {"id": "1"}]
        result = UniquenessValidator.within_batch(records, "id")
        assert not result.valid

    def test_within_batch_passes_for_unique_values(self) -> None:
        records = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        assert UniquenessValidator.within_batch(records, "id").valid

    def test_against_existing_detects_collision(self) -> None:
        result = UniquenessValidator.against_existing(
            "A01", existing_values=["A01", "A02"], field="tenant_code"
        )
        assert not result.valid

    def test_against_existing_passes_for_new_value(self) -> None:
        result = UniquenessValidator.against_existing(
            "A03", existing_values=["A01", "A02"], field="tenant_code"
        )
        assert result.valid


class TestRelationshipValidator:
    def test_foreign_key_exists_passes(self) -> None:
        tenants = TenantBuilder().build_many(2)
        tenant_ids = [t.tenant_id for t in tenants]
        subscriber = asdict(SubscriberBuilder().with_tenant_id(tenant_ids[0]).build())
        result = RelationshipValidator.foreign_key_exists(
            [subscriber], foreign_key_field="tenant_id", referenced_values=tenant_ids
        )
        assert result.valid

    def test_foreign_key_missing_fails(self) -> None:
        subscriber = asdict(SubscriberBuilder().with_tenant_id("ORPHAN").build())
        result = RelationshipValidator.foreign_key_exists(
            [subscriber], foreign_key_field="tenant_id", referenced_values=["T1", "T2"]
        )
        assert not result.valid


class TestSchemaValidator:
    def test_valid_record_passes_schema(self) -> None:
        subscriber = asdict(SubscriberBuilder().build())
        schema = {
            "type": "object",
            "required": ["subscriber_id", "msisdn"],
            "properties": {"msisdn": {"type": "string"}},
        }
        assert SchemaValidator.validate(subscriber, schema).valid

    def test_missing_required_field_fails_schema(self) -> None:
        schema = {"type": "object", "required": ["subscriber_id"]}
        result = SchemaValidator.validate({}, schema)
        assert not result.valid

    def test_has_required_fields_detects_missing(self) -> None:
        result = SchemaValidator.has_required_fields({"a": 1}, ["a", "b"])
        assert not result.valid

    def test_has_required_fields_passes_when_present(self) -> None:
        assert SchemaValidator.has_required_fields({"a": 1, "b": 2}, ["a", "b"]).valid
