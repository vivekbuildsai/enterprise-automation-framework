from __future__ import annotations

from typing import Any

import jsonschema

from framework.testdata.validators.validation_result import ValidationResult


class SchemaValidator:
    """Validates a record against a JSON Schema — for test data whose
    *shape* (required fields present, correct types) matters more than any
    single field's business meaning. Complements `BusinessRuleValidator`
    (semantic rules) and `FormatValidator` (identifier formats) rather than
    replacing them.
    """

    @staticmethod
    def validate(record: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
        validator = jsonschema.Draft202012Validator(schema)
        errors = [
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in validator.iter_errors(record)
        ]
        return ValidationResult(valid=not errors, errors=errors)

    @staticmethod
    def has_required_fields(record: dict[str, Any], required_fields: list[str]) -> ValidationResult:
        missing = [
            field for field in required_fields if field not in record or record[field] in (None, "")
        ]
        if missing:
            return ValidationResult.fail(f"Missing required field(s): {missing}")
        return ValidationResult.ok()
