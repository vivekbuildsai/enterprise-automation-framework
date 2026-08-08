from __future__ import annotations

from typing import Any

from framework.testdata.masking.pii_fields import PII_FIELDS


class DataMasker:
    """Masks sensitive fields in a record before it leaves the immediate
    test process — logged, exported, or attached to an Allure report — so
    a captured artifact never carries a real-looking MSISDN/email/password
    in the clear. Operates on plain dicts (`dataclasses.asdict(entity)`
    first) so it works uniformly across every builder-produced entity.
    """

    @staticmethod
    def mask_value(value: str, *, visible_start: int = 2, visible_end: int = 2) -> str:
        if len(value) <= visible_start + visible_end:
            return "*" * len(value)
        hidden = "*" * (len(value) - visible_start - visible_end)
        return value[:visible_start] + hidden + value[-visible_end:]

    @staticmethod
    def mask_record(
        record: dict[str, Any], *, fields: frozenset[str] | set[str] | None = None
    ) -> dict[str, Any]:
        """Partial masking — keeps a few characters visible at each end
        (e.g. `"44******23"`), useful for logs a human still needs to
        eyeball for "does this look like the right record" without
        exposing the real value.
        """
        target_fields = fields if fields is not None else PII_FIELDS
        masked = dict(record)
        for field in target_fields:
            if field in masked and isinstance(masked[field], str):
                masked[field] = DataMasker.mask_value(masked[field])
        return masked

    @staticmethod
    def redact_record(
        record: dict[str, Any], *, fields: frozenset[str] | set[str] | None = None
    ) -> dict[str, Any]:
        """Full redaction — for exports/logs that must not leak even a
        masked fragment.
        """
        target_fields = fields if fields is not None else PII_FIELDS
        redacted = dict(record)
        for field in target_fields:
            if field in redacted:
                redacted[field] = "***REDACTED***"
        return redacted
