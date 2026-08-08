from __future__ import annotations

# Declarative registry of field names this framework's builders/generators
# produce that are considered sensitive by default — masking/export code
# reads this instead of every call site maintaining its own list.
PII_FIELDS: frozenset[str] = frozenset(
    {
        "email",
        "msisdn",
        "imsi",
        "iccid",
        "password",
        "first_name",
        "last_name",
        "username",
        "full_address",
        "street_address",
        "date_of_birth",
    }
)
