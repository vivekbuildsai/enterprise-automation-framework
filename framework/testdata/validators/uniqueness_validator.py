from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from framework.testdata.validators.validation_result import ValidationResult


class UniquenessValidator:
    """Checks that a field's values are unique — either within a batch of
    generated records (catching a builder/generator collision before it
    ever reaches the database) or against an existing set of values already
    seeded (catching a collision with prior test data).
    """

    @staticmethod
    def within_batch(records: Iterable[dict[str, Any]], field: str) -> ValidationResult:
        values = [record[field] for record in records if field in record]
        duplicates = {value for value in values if values.count(value) > 1}
        if duplicates:
            dup_values = sorted(map(str, duplicates))
            return ValidationResult.fail(
                f"Field '{field}' has duplicate values in batch: {dup_values}"
            )
        return ValidationResult.ok()

    @staticmethod
    def against_existing(
        value: Any, *, existing_values: Iterable[Any], field: str
    ) -> ValidationResult:
        if value in set(existing_values):
            return ValidationResult.fail(f"Field '{field}' value '{value}' already exists")
        return ValidationResult.ok()
