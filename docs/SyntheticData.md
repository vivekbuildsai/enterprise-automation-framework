# Synthetic Data, Masking & Encryption

How `framework/testdata/generators/`, `masking/`, and `synthetic/` support
"dummy production-like datasets" with no real PII and no hardcoded
credentials.

## Random & telecom identifier generation

`framework.utilities.RandomData` (extended additively this milestone with
`street_address`/`city`/`full_address`/`date_of_birth`/`date_between`/...)
covers general-purpose fields. `framework/testdata/generators/
TelecomIdentifierGenerator` covers telecom-specific ones:

| Method | Produces | Rule |
|---|---|---|
| `imei()` | 15-digit IMEI | 8-digit TAC + 6-digit serial + Luhn check digit |
| `iccid()` | 19-digit ICCID | issuer identifier + account ID + Luhn check digit |
| `imsi(mcc=, mnc=)` | up to 15-digit IMSI | MCC + MNC + MSIN |
| `msisdn(country_code=)` | E.164-style number | country code + subscriber digits |
| `plmn_id()`, `cell_id()`, `tracking_area_code()` | network identifiers | |
| `ip_address_v4()` | dotted-quad IPv4 | |

IMEI/ICCID are genuinely Luhn-valid (`framework.testdata.utilities.
luhn_checksum`) — the same checksum algorithm real devices/SIMs are
validated against — so generated identifiers pass any Luhn-based format
check downstream, not just casual inspection. None of these correspond to
a real, allocated device/subscriber.

## Deterministic (repeatable) generation

`DeterministicGenerator.seeded_context(seed)` seeds both Python's `random`
module (used directly by `TelecomIdentifierGenerator`) and Faker's shared
generator (used by `RandomData`) for the duration of a `with` block, then
restores whatever random state was active before — so one deterministic
dataset generation doesn't make every later, unrelated call in the same
test session predictable too:

```python
with DeterministicGenerator.seeded_context(1234):
    subscriber = SubscriberBuilder().build()   # same msisdn/imsi every time seed=1234 is used
```

Use this for datasets that must diff cleanly between CI runs, or to
reproduce the exact data behind a bug report.

## Custom generators

`framework.testdata.generators.custom_generators` (a shared
`CustomGeneratorRegistry`) — register a project-specific generator once,
call it by name anywhere:

```python
custom_generators.register("employee_id", lambda: f"EMP-{random.randint(1000,9999)}")
custom_generators.generate("employee_id")
```

## Masking

`framework.testdata.masking.DataMasker` — for values that must not appear
in the clear in logs/exports/Allure attachments:

```python
DataMasker.mask_value("447700900123")          # "44********23" — partial, still eyeballable
DataMasker.mask_record(record)                  # masks every field in PII_FIELDS present in `record`
DataMasker.redact_record(record, fields={...})  # full "***REDACTED***", no fragment visible
```

`PII_FIELDS` (`masking/pii_fields.py`) is the declarative registry of which
field names are considered sensitive by default — extend it (or pass an
explicit `fields=` set) rather than hardcoding a list at each call site.

## Encryption

`framework.testdata.masking.TestDataEncryption` wraps
`framework.database.utilities.secrets.CredentialResolver`'s Fernet
encrypt/decrypt (the same mechanism the database layer's
`encrypted_password` config field already uses — reused, not
reimplemented) for encrypting test-data values at rest, distinct from live
database credentials which should keep going through `CredentialResolver`
directly.

```python
key = TestDataEncryption.generate_key()
ciphertext = TestDataEncryption.encrypt("sensitive-value", key)
plaintext = TestDataEncryption.decrypt(ciphertext, key)
```

The key itself must only ever live in the environment/secrets manager —
same rule as `AUTOMATION_DB_SECRET_KEY` in
[DatabaseConfiguration.md](DatabaseConfiguration.md#encrypted-credentials).

## Synthetic bulk data & anonymization

`framework.testdata.synthetic.SyntheticDatasetGenerator` — explicitly-named
wrapper over `BaseBuilder.build_many()`/a builder-factory loop, for volume/
load test data:

```python
SyntheticDatasetGenerator.generate(SubscriberBuilder().gold_tier(), 1000)
SyntheticDatasetGenerator.generate_with_variation(lambda: SubscriberBuilder().blocked(), 50)
```

`framework.testdata.synthetic.Anonymizer` — replaces PII fields in a
**real-shaped** record with freshly-generated synthetic equivalents, for
teams that need production-*like* volume/shape data without any real
subscriber's actual PII surviving into a test environment:

```python
Anonymizer.anonymize(real_shaped_record, fields={"email", "msisdn", "imsi"})
```

`Anonymizer` produces a still-*usable* synthetic value; `DataMasker`
produces an obscured, unusable one — pick based on whether the downstream
test needs the field to still look/behave like real data.

## No hardcoded credentials

Every builder that produces a password (`UserBuilder`) generates one via
`RandomData.password()` by default — nothing in this layer ships a literal
`"password123"` default. Secrets a test genuinely needs (a real API key,
a real DB password) come from `EnvironmentVariableProvider` or
`CredentialResolver`, never a literal in code.

## Testing

`tests/testdata/unit/test_generators.py`, `test_masking.py`,
`test_synthetic.py` — 24 tests, including a statistical sanity check that
generated IMEIs are genuinely Luhn-valid by construction (not coincidence
— a random 15-digit string only passes Luhn ~10% of the time).
