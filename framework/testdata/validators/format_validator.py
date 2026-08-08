from __future__ import annotations

import re

from framework.testdata.utilities.luhn import is_luhn_valid
from framework.testdata.validators.validation_result import ValidationResult

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FormatValidator:
    """Structural/format checks for the identifiers `framework.testdata.
    generators.TelecomIdentifierGenerator` produces, plus common
    general-purpose formats (email). Deliberately checks *shape*, not
    real-world allocation — "is this a syntactically valid IMEI" not "is
    this IMEI assigned to a real device".
    """

    @staticmethod
    def is_valid_email(value: str) -> ValidationResult:
        if _EMAIL_PATTERN.match(value):
            return ValidationResult.ok()
        return ValidationResult.fail(f"'{value}' is not a valid email address")

    @staticmethod
    def is_valid_imei(value: str) -> ValidationResult:
        if len(value) == 15 and is_luhn_valid(value):
            return ValidationResult.ok()
        return ValidationResult.fail(f"'{value}' is not a valid IMEI (15 digits, Luhn checksum)")

    @staticmethod
    def is_valid_iccid(value: str) -> ValidationResult:
        if 19 <= len(value) <= 20 and value.isdigit() and is_luhn_valid(value):
            return ValidationResult.ok()
        return ValidationResult.fail(
            f"'{value}' is not a valid ICCID (19-20 digits, Luhn checksum)"
        )

    @staticmethod
    def is_valid_imsi(value: str) -> ValidationResult:
        if value.isdigit() and 6 <= len(value) <= 15:
            return ValidationResult.ok()
        return ValidationResult.fail(f"'{value}' is not a valid IMSI (6-15 digits)")

    @staticmethod
    def is_valid_msisdn(value: str) -> ValidationResult:
        if value.isdigit() and 8 <= len(value) <= 15:
            return ValidationResult.ok()
        return ValidationResult.fail(f"'{value}' is not a valid MSISDN (8-15 digits, E.164-style)")
