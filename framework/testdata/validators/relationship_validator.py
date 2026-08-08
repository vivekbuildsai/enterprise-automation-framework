from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from framework.testdata.validators.validation_result import ValidationResult


class RelationshipValidator:
    """Checks referential integrity within a composed set of test data —
    e.g. every `Subscriber.tenant_id` in a batch must match a `tenant_id`
    that's actually present among the tenants being seeded alongside it.
    Exactly the kind of mistake that's easy to make hand-assembling
    `ScenarioLibrary`-style entity bundles and easy to miss until the
    database rejects (or silently accepts, worse) an orphaned foreign key.
    """

    @staticmethod
    def foreign_key_exists(
        records: Iterable[dict[str, Any]],
        *,
        foreign_key_field: str,
        referenced_values: Iterable[Any],
    ) -> ValidationResult:
        referenced = set(referenced_values)
        errors = [
            f"Record has {foreign_key_field}='{record[foreign_key_field]}' which does not "
            f"match any referenced value"
            for record in records
            if foreign_key_field in record and record[foreign_key_field] not in referenced
        ]
        return ValidationResult(valid=not errors, errors=errors)
