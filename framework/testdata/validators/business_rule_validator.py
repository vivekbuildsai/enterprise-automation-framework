from __future__ import annotations

from collections.abc import Callable
from typing import Any

from framework.testdata.validators.validation_result import ValidationResult

RuleFn = Callable[[dict[str, Any]], ValidationResult]


class BusinessRuleValidator:
    """Named, pluggable business-rule checks against a record (a plain
    dict, or `dataclasses.asdict(entity)`). Register once, validate
    anywhere, instead of scattering ad hoc `if record["cos"] not in
    {...}: raise` checks through test code. Rules should return `ok()`
    when the field they check isn't present in the record at all (not
    applicable to that record type), and only `fail()` when the field is
    present with an invalid value — that's what makes `validate()` safe to
    call with every registered rule by default instead of requiring the
    caller to pick which rules apply to which record shape.
    """

    def __init__(self) -> None:
        self._rules: dict[str, RuleFn] = {}

    def register(self, name: str, rule: RuleFn) -> None:
        self._rules[name] = rule

    def unregister(self, name: str) -> None:
        self._rules.pop(name, None)

    def validate(
        self, record: dict[str, Any], *, rule_names: list[str] | None = None
    ) -> ValidationResult:
        names = rule_names if rule_names is not None else list(self._rules)
        results = [self._rules[name](record) for name in names]
        return ValidationResult.combine(results)


def _cos_is_valid_tier(record: dict[str, Any]) -> ValidationResult:
    if "cos" not in record:
        return ValidationResult.ok()
    valid_tiers = {"Gold", "Silver", "Bronze"}
    if record["cos"] in valid_tiers:
        return ValidationResult.ok()
    return ValidationResult.fail(f"cos '{record['cos']}' is not one of {sorted(valid_tiers)}")


def _steering_flags_are_mutually_exclusive(record: dict[str, Any]) -> ValidationResult:
    if "leakage_flag" not in record or "anti_sor_flag" not in record:
        return ValidationResult.ok()
    if record["leakage_flag"] and record["anti_sor_flag"]:
        return ValidationResult.fail(
            "leakage_flag and anti_sor_flag cannot both be set — leakage means steering "
            "was attempted and failed, anti-SoR means steering was never applied"
        )
    return ValidationResult.ok()


def _amount_is_non_negative(record: dict[str, Any]) -> ValidationResult:
    if "amount" not in record:
        return ValidationResult.ok()
    if record["amount"] < 0:
        return ValidationResult.fail(f"amount {record['amount']} must not be negative")
    return ValidationResult.ok()


business_rules = BusinessRuleValidator()
business_rules.register("cos_is_valid_tier", _cos_is_valid_tier)
business_rules.register(
    "steering_flags_are_mutually_exclusive", _steering_flags_are_mutually_exclusive
)
business_rules.register("amount_is_non_negative", _amount_is_non_negative)
