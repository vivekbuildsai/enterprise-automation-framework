# Builder Pattern

How `framework/testdata/builders/` implements the Builder pattern, and why
it's shaped the way it is.

## `BaseBuilder[T]`

Every domain builder extends `BaseBuilder[T]` (`base_builder.py`):

```python
class BaseBuilder(ABC, Generic[T]):
    def __init__(self) -> None:
        self._fields: dict[str, Any] = {}

    def _set(self, **kwargs: Any) -> Self: ...       # internal — subclasses' with_x() call this
    def with_fields(self, **kwargs: Any) -> Self: ... # public escape hatch for generic callers
    def _get(self, field: str, default_factory: Any) -> Any: ...  # lazy default resolution

    @abstractmethod
    def build(self) -> T: ...

    def build_many(self, count: int) -> list[T]: ...
```

**Defaults are lazy, not eager.** `_get(field, default_factory)` only calls
`default_factory()` inside `build()`, for whichever fields weren't
explicitly set. This is what makes `build_many(count)` useful:

```python
subscribers = SubscriberBuilder().gold_tier().build_many(5)
# 5 distinct subscriber_id/msisdn/imsi values, all sharing cos="Gold"
# (explicitly set) — not 5 copies of one record.
```

If defaults were generated at construction time instead, every `build()`
call on the same builder would return the same record.

## The 8 domain builders

| Builder | Produces | Notes |
|---|---|---|
| `TenantBuilder` | `framework.database.models.Tenant` | reused, not duplicated |
| `NetworkBuilder` | `framework.database.models.Network` | |
| `SubscriberBuilder` | `framework.database.models.Subscriber` | MSISDN/IMSI default to `TelecomIdentifierGenerator` |
| `SteeringRuleBuilder` | `framework.database.models.SteeringZone` | leakage/anti-SoR flags via `.with_leakage()`/`.with_anti_sor()` |
| `AlarmBuilder` | `framework.database.models.Alarm` | `.critical()`, `.cleared()` |
| `SIMBuilder` | `SimCard` (new, `builders/models.py`) | ICCID/IMSI/MSISDN telecom-identifier defaults |
| `BillingBuilder` | `BillingRecord` (new) | `.paid()`, `.overdue()`, `.billing_error()` |
| `UserBuilder` | `UserProfile` (new) | `.to_api_create_request()` maps to the API layer's `CreateUserRequest` shape |

Each exposes `with_x()` fluent setters (return `self`/the builder type, not
`Self` from `typing` at the call site — every method is typed to return its
own class so IDE autocomplete stays accurate through a chain) plus a small
number of named shortcuts for common states (`.active()`, `.blocked()`,
`.gold_tier()`, ...).

```python
subscriber = (
    SubscriberBuilder()
    .with_tenant_id(tenant.tenant_id)
    .gold_tier()
    .blocked()
    .build()
)
```

## Why builders produce existing dataclasses, not new DTOs

`TenantBuilder().build()` returns a real `framework.database.models.Tenant`
— the exact type `TenantRepository.create()` accepts and
`TenantValidator.verify_against_database()` compares against. There's no
translation step between "test data" and "the object the DB/validation
layer expects." This is why builders live in `framework/testdata/` but
import from `framework/database/models` rather than the reverse — TDM is a
consumer of the domain model, not its owner.

## Factories: canned instances on top of builders

`framework/testdata/factories/` wraps each builder with named,
zero-argument (plus `**overrides`) convenience methods:

```python
class SubscriberFactory:
    @staticmethod
    def active(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().active().with_fields(**overrides).build()

    @staticmethod
    def premium(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().active().gold_tier().with_fields(**overrides).build()
```

Use a builder directly when a test needs several fields customized; use a
factory when the test just needs "a premium subscriber" and the specific
field values don't matter. `**overrides` (routed through `with_fields()`,
`BaseBuilder`'s public escape hatch) covers the occasional case where a
factory's canned shape needs one field different.

## Testing

`tests/testdata/unit/test_builders.py` and `test_factories.py` cover every
builder/factory: fluent chaining, default generation, explicit-override
precedence, and `build_many()` distinctness — 24 tests, no database or
network required (pure in-memory object construction).
