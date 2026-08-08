# Scenario Library

`framework/testdata/scenarios/ScenarioLibrary` — ten named, reusable
business scenarios, each composing builders/factories into a coherent,
referentially-consistent bundle of entities. A `Scenario` built once is
usable unmodified by a UI test, an API test, and a DB test alike — see
[TestDataFramework.md](TestDataFramework.md) for how this fits the rest of
the TDM layer.

## `Scenario`

```python
@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    description: str
    entities: dict[str, Any]
    tags: tuple[str, ...] = ()

    def get(self, entity_name: str) -> Any: ...       # raises KeyError with the available keys listed
    def all_entities(self) -> list[Any]: ...           # every entity, in dependency-safe insertion order
```

## The 10 scenarios

| Scenario | Entities | What it represents |
|---|---|---|
| `new_subscriber()` | tenant, network, subscriber | A freshly onboarded, active subscriber with no history. |
| `roaming_subscriber()` | tenant, network, subscriber, zone, sim | An active subscriber currently roaming in a steered zone. |
| `blocked_subscriber()` | tenant, network, subscriber | A subscriber whose line has been blocked. |
| `premium_customer()` | tenant, network, subscriber, billing | Gold-tier subscriber with an up-to-date, paid plan. |
| `enterprise_customer(line_count=5)` | tenant, network, subscribers (list) | A tenant with N active subscriber lines under one account. |
| `inactive_sim()` | tenant, subscriber, sim | An active subscriber whose SIM was never activated. |
| `expired_subscription()` | tenant, subscriber, billing | Subscription lapsed, with an overdue bill. |
| `alarm_raised()` | tenant, network, zone, alarm | A critical alarm against a leaking steering zone. |
| `network_failure()` | tenant, network, zone, alarm | A degraded network with a corresponding critical alarm. |
| `billing_error()` | tenant, subscriber, billing | A subscriber whose latest billing run failed. |

## Referential consistency

Every scenario threads IDs correctly between its entities — a subscriber's
`tenant_id` always matches the tenant it was built alongside, a zone's
`network_id` matches its network, and so on:

```python
scenario = ScenarioLibrary.roaming_subscriber()
tenant = scenario.get("tenant")
subscriber = scenario.get("subscriber")
zone = scenario.get("zone")

assert subscriber.tenant_id == tenant.tenant_id
assert zone.tenant_id == tenant.tenant_id
```

This is verified for every scenario in
`tests/testdata/unit/test_scenarios.py` (referential-consistency + the
default-relationship assertions per scenario), not just asserted in this
doc.

## Using a scenario in a test

**Direct**, when you just need the built objects:

```python
from framework.testdata.scenarios import ScenarioLibrary

scenario = ScenarioLibrary.premium_customer()
subscriber = scenario.get("subscriber")
```

**Via the `seeded_scenario` fixture**, when the test needs the scenario's
DB-backed entities actually persisted, with automatic cleanup:

```python
def test_premium_customer_sees_correct_billing(seeded_scenario, subscriber_repository):
    handle = seeded_scenario("premium_customer")
    subscriber = next(e for e in handle.database_entities if type(e).__name__ == "Subscriber")
    assert subscriber_repository.get_by_id(subscriber.subscriber_id).cos == "Gold"
    # cleanup happens automatically after the test — see CleanupStrategy.md
```

`seeded_scenario` seeds only the entities that have a database repository
mapping (`Tenant`/`Network`/`Subscriber`/`SteeringZone`/`Alarm`) — a
scenario like `roaming_subscriber()` that also includes a `SimCard` (no DB
table) skips it by default; pass `strict=True` to raise instead of
skipping if a test specifically needs every entity to be DB-backed.

## Adding a new scenario

Add a `@staticmethod` to `ScenarioLibrary` composing existing
builders/factories — keep IDs threaded correctly between entities (a
review checklist item, not automatically enforced beyond the referential-
consistency tests already covering the 10 built-in scenarios) and give it
a `tags` tuple so it's discoverable by theme. No other layer needs to
change — `DatabaseSeeder.seed_scenario()` and the `seeded_scenario` fixture
work with any `Scenario`, not a hardcoded list of names.
