# Test Data Management — Best Practices

Practical guidance for using `framework/testdata/` well, and the reasoning
behind each rule.

## Never hardcode business data in a test

```python
# Don't:
subscriber = Subscriber(subscriber_id="S1", msisdn="447700900123", ...)

# Do:
subscriber = SubscriberFactory.active()
```

The literal-values version breaks the moment two tests run in parallel and
both try to create `"S1"`, tells a reader nothing about *why* those values
were chosen, and can't be swapped for a different scenario without editing
the test. `SubscriberFactory.active()` (or `SubscriberBuilder()` for
customization, or `seeded_scenario("...")` for a whole related bundle) is
always unique, always intention-revealing, and always reusable elsewhere.

## Pick the right entry point

| Need | Use |
|---|---|
| One record, default shape is fine | A factory (`SubscriberFactory.active()`) |
| One record, need specific fields | A builder (`SubscriberBuilder().with_cos("Gold").build()`) |
| Several related records for a business situation | `ScenarioLibrary` / `seeded_scenario("name")` fixture |
| QA-authored or environment-specific fixed data | `DatasetLoader`/`load_dataset` fixture |
| Bulk/volume data | `SyntheticDatasetGenerator.generate(builder, count)` |

Don't reach for a bigger tool than the test needs — a test asserting one
field on one subscriber doesn't need a full scenario.

## Let the TDM layer own IDs

Every builder generates its own ID by default (`IdSequenceGenerator`/
`RandomData.uuid()`) — don't invent your own `f"test-subscriber-{i}"`
scheme in test code. This is what makes parallel test execution safe: two
tests building a `SubscriberBuilder()` never collide, because neither
picked its own ID.

## Always seed and clean up through the same mechanism

If a test seeds via `seeded_scenario`, don't also hand-write a repository
`.create()` call for one more record without registering its cleanup too —
either extend the scenario, or register the extra entity's cleanup
explicitly with the injected `cleanup_registry` fixture. A test that seeds
more than it cleans up is exactly the leak this layer exists to prevent.

## Prefer scenario composition over ad hoc entity assembly

```python
# Fragile — easy to get tenant_id/network_id wrong between entities:
tenant = TenantBuilder().build()
subscriber = SubscriberBuilder().with_tenant_id(tenant.tenant_id).build()
zone = SteeringRuleBuilder().with_tenant_id(tenant.tenant_id).build()  # forgot network_id!

# Robust — ScenarioLibrary already got the relationships right, and it's tested:
scenario = ScenarioLibrary.roaming_subscriber()
```

If a business situation recurs across more than one test, it belongs in
`ScenarioLibrary`, not copy-pasted builder chains.

## Mask/anonymize before anything leaves the process

Any log line, exported file, or report that might include a subscriber's
MSISDN/email/etc. should go through `DataMasker` or `Anonymizer` first —
see [SyntheticData.md](SyntheticData.md). This applies even to synthetic
data (it's realistic-looking, so treat it with the same care as real data
in shared artifacts, even though it isn't actually sensitive).

## Deterministic generation is for reproducibility, not for hiding randomness

Use `DeterministicGenerator.seeded_context(seed)` when you specifically
need a dataset to be identical across runs (diffing CI output, reproducing
a bug). Don't reach for it by default — most tests should exercise fresh,
independently-random data each run, which is far better at catching
edge-case bugs a fixed seed would never generate.

## Cross-layer consistency: build once, use everywhere

A `Scenario`'s entities are plain dataclasses — the same object can be
handed to a repository (`DatabaseSeeder`), converted to an API payload
(`UserProfile.to_api_create_request()`), and compared against in a
validator (`SubscriberValidator.verify_against_database()`), without a
translation layer in between. When adding a new builder, prefer reusing an
existing `framework.database.models` dataclass over inventing a new DTO —
see [BuilderPattern.md](BuilderPattern.md).

## Test the TDM layer itself, not just with it

Every package under `framework/testdata/` has direct unit/integration
coverage (`tests/testdata/`) independent of any specific downstream test —
generators are checked for actual format validity (Luhn checksums, correct
digit counts), not just "didn't crash". When extending this layer, add
tests at that level too, not only via whatever test happens to consume
the new builder/generator.

## See also

- [TestDataFramework.md](TestDataFramework.md) — architecture overview
- [BuilderPattern.md](BuilderPattern.md) — builder/factory design
- [ScenarioLibrary.md](ScenarioLibrary.md) — the 10 named scenarios
- [DatasetManagement.md](DatasetManagement.md) — file-based data
- [SyntheticData.md](SyntheticData.md) — generation, masking, encryption
- [CleanupStrategy.md](CleanupStrategy.md) — seed/cleanup mechanics
- [DatabaseBestPractices.md](DatabaseBestPractices.md) — the database
  layer's own best practices (dialect portability, transaction modes),
  which this layer's `DatabaseSeeder`/`DatabaseCleanupService` build on top
  of and inherit
