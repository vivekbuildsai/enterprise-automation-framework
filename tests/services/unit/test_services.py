from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from framework.database.clickhouse.validator import ClickHouseValidator
from framework.models import Brand
from framework.services import ValidationService

pytestmark = pytest.mark.smoke


class TestValidationService:
    def test_delegates_to_the_clickhouse_validator_with_expected_first(self) -> None:
        clickhouse_validator = MagicMock(spec=ClickHouseValidator)
        service = ValidationService(clickhouse_validator)

        service.verify_ui_against_database(
            {"name": "Acme"}, {"name": "Acme"}, fields=["name"], name="Brand check"
        )

        clickhouse_validator.verify.assert_called_once_with(
            {"name": "Acme"}, {"name": "Acme"}, fields=["name"], name="Brand check"
        )

    def test_real_end_to_end_match(self) -> None:
        service = ValidationService(ClickHouseValidator())
        result = service.verify_ui_against_database(
            {"code": "ACM"}, {"code": "ACM"}, fields=["code"]
        )
        assert result.matched is True

    def test_real_end_to_end_mismatch(self) -> None:
        service = ValidationService(ClickHouseValidator())
        result = service.verify_ui_against_database(
            {"code": "ACM"}, {"code": "DIFFERENT"}, fields=["code"]
        )
        assert result.matched is False


def test_brand_model_survives_a_round_trip_through_validation_service() -> None:
    """Smoke-level check that Brand (framework.models) plugs into the
    generic ValidationService without special-casing.
    """
    from dataclasses import asdict

    brand = Brand(name="Acme Mobile", code="ACM")
    service = ValidationService(ClickHouseValidator())

    result = service.verify_ui_against_database(asdict(brand), asdict(brand))

    assert result.matched is True
