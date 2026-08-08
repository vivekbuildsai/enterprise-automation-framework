from __future__ import annotations

from dataclasses import dataclass, field

from framework.exceptions import TestDataError


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Uniform result shape every validator in `framework.testdata.
    validators` returns — mirrors `framework.database.utilities.comparison.
    ComparisonResult`'s "return a result, don't just raise" design so
    callers can inspect every check before deciding what's fatal.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise TestDataError("; ".join(self.errors))

    @staticmethod
    def ok() -> ValidationResult:
        return ValidationResult(valid=True)

    @staticmethod
    def fail(*errors: str) -> ValidationResult:
        return ValidationResult(valid=False, errors=list(errors))

    @staticmethod
    def combine(results: list[ValidationResult]) -> ValidationResult:
        errors = [error for result in results for error in result.errors]
        return ValidationResult(valid=not errors, errors=errors)
