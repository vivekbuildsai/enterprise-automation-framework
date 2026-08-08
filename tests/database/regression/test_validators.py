from __future__ import annotations

import pytest
from sqlalchemy.engine import Connection

from framework.database.exceptions import DataComparisonError
from framework.database.models import Subscriber
from framework.database.repositories import SteeringRepository, SubscriberRepository
from framework.database.validators import DatabaseValidator, SteeringValidator, SubscriberValidator

pytestmark = [pytest.mark.regression, pytest.mark.database]


def _create_subscriber(repo: SubscriberRepository, conn: Connection) -> None:
    repo.create(
        Subscriber(
            subscriber_id="S1",
            msisdn="447700900123",
            imsi="234000000000001",
            status="ACTIVE",
            cos="Gold",
            tenant_id="T1",
            network_id="N1",
            created_at="t",
            updated_at="t",
        )
    )
    conn.commit()


def test_subscriber_validator_matches_against_database(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    validator = SubscriberValidator(subscriber_repository)

    result = validator.verify_against_database(
        "S1",
        {"msisdn": "447700900123", "status": "ACTIVE", "cos": "Gold"},
        fields=["msisdn", "status", "cos"],
    )
    assert result.matched


def test_subscriber_validator_detects_api_mismatch(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    validator = SubscriberValidator(subscriber_repository)

    expected = {"status": "ACTIVE", "cos": "Gold"}
    api_payload = {"status": "ACTIVE", "cos": "Silver"}  # deliberately wrong
    result = validator.verify_against_api(api_payload, expected, fields=["status", "cos"])

    assert not result.matched
    assert result.diffs[0].field == "cos"


def test_subscriber_validator_verify_all_or_raise_raises_on_any_mismatch(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    validator = SubscriberValidator(subscriber_repository)

    with pytest.raises(DataComparisonError):
        validator.verify_all_or_raise(
            "S1",
            expected={"status": "ACTIVE", "cos": "Gold"},
            api_payload={"status": "ACTIVE", "cos": "Silver"},
            fields=["status", "cos"],
        )


def test_subscriber_validator_verify_all_or_raise_passes_when_every_layer_agrees(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    validator = SubscriberValidator(subscriber_repository)

    results = validator.verify_all_or_raise(
        "S1",
        expected={"status": "ACTIVE", "cos": "Gold"},
        api_payload={"status": "ACTIVE", "cos": "Gold"},
        ui_values={"status": "Active", "cos": "gold"},
        fields=["status", "cos"],
    )
    assert len(results) == 3
    assert all(r.matched for r in results)


def test_steering_validator_matches_against_database(
    db_schema: None, db_connection: Connection, steering_repository: SteeringRepository
) -> None:
    from framework.database.models import SteeringZone

    steering_repository.create(
        SteeringZone(
            zone_id="Z1",
            zone_code="Country_A",
            country="Country_A",
            tenant_id="T1",
            network_id="N1",
            tr_type="LBTR",
            cos="Gold",
            ota_region="EMEA",
            roamer_count=120,
            data_usage_mb=4500,
            leakage_flag=1,
            anti_sor_flag=0,
            status="ACTIVE",
            modified_by="Admin",
            modified_date="t",
        )
    )
    db_connection.commit()

    validator = SteeringValidator(steering_repository)
    result = validator.verify_against_database(
        "Z1", {"tr_type": "LBTR", "leakage_flag": 1}, fields=["tr_type", "leakage_flag"]
    )
    assert result.matched


def test_generic_database_validator_accepts_dataclass_or_dict(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    subscriber = subscriber_repository.get_by_id("S1")

    result = DatabaseValidator.verify_matches(
        subscriber, {"status": "ACTIVE"}, entity_label="Subscriber", fields=["status"]
    )
    assert result.matched

    result_dict = DatabaseValidator.verify_matches(
        {"status": "ACTIVE"}, {"status": "ACTIVE"}, entity_label="Subscriber", fields=["status"]
    )
    assert result_dict.matched


def test_generic_database_validator_or_raise_raises_on_mismatch(
    db_schema: None, db_connection: Connection, subscriber_repository: SubscriberRepository
) -> None:
    _create_subscriber(subscriber_repository, db_connection)
    subscriber = subscriber_repository.get_by_id("S1")

    with pytest.raises(DataComparisonError):
        DatabaseValidator.verify_matches_or_raise(
            subscriber, {"status": "SUSPENDED"}, entity_label="Subscriber", fields=["status"]
        )
