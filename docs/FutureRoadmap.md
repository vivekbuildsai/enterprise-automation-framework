# Future Roadmap

Build order for the modules scaffolded but not yet implemented. Each milestone
should land as its own set of commits and be verified (tests green, linters
clean) before the next starts — same discipline as Milestones 1-3.

## Milestone 2 — API layer ✅ done

- `framework/api`: httpx-based REST client (`ApiClient`) with retry/timeout,
  pluggable auth (Bearer/JWT/Basic/API Key/Cookie/OAuth2 client-credentials/
  OAuth2 authorization-code), JSON Schema response validation, fluent
  `RequestBuilder`/`ResponseValidator`, Pydantic models, centralized
  `Endpoints` registry, `AuthService`/`UserService`/`ApiValidator`.
- Proven end-to-end against dummyjson.com (reqres.in now requires a paid
  signup API key, so it wasn't usable): 117 tests, 99% coverage on
  `framework/api`, live smoke/regression/negative suites + an offline
  `httpx.MockTransport` unit layer.
- See [APIFramework.md](APIFramework.md) for the full writeup.

## Milestone 3 — Enterprise UI Page Object framework ✅ done

(Originally planned as "hybrid validation wiring + database layer" — the
actual request that landed as Milestone 3 was a full enterprise-grade UI
automation upgrade instead; that plan moves to Milestone 4 below.)

- `framework/waits/WaitManager`, `framework/locators/Locators` (testid > role
  > label > css > xpath), `BasePage`/`BaseComponent` extended with the full
  interaction surface (double/right-click, hover, drag-drop, keyboard,
  mouse, upload/download, scroll, frame/tab/window switching, highlight).
- 14 reusable components (`framework/components`): Header, Sidebar,
  TopNavigation, Breadcrumb, Modal, ConfirmationDialog, Notification,
  SearchBox, DatePicker, Dropdown, TreeView, Table, Pagination, Grid.
- `framework/navigation/AppNavigator`, a Workflow layer
  (`framework/workflows`: Login/Logout/SubscriberSearch/PolicyCreation/
  UserCreation), `UIAssert` (`framework/assertions`).
- `TestDataLoader` (JSON/CSV/Excel/environment-specific) and per-module
  Pydantic test-data builders backed by `RandomData` (Faker).
- `AccessibilityChecker` (axe-core via `axe-playwright-python`) and
  `VisualComparator` (Pillow screenshot-diff) — both proven against real
  pages, not just unit-tested in isolation.
- 9 sample module page objects under `framework/pages/`: Authentication and
  Dashboard (real, from Milestone 1), Subscriber Management (real,
  live-verified against the-internet.herokuapp.com's `/tables` demo — a
  stand-in target since this is a generic, customer-agnostic framework),
  and Policy Management/Alarm Management/Reports/Administration/Audit
  Logs/User Management (complete real code — Page Object + Workflow +
  Assertions + Test Data + example test — with the example test
  `pytest.mark.skip`'d until a real target application is configured).
- `ApiValidator` (Milestone 2) still implements the API-facing half of
  hybrid validation; the `ValidationFacade` that would dispatch UI/API/DB
  checks by `ValidationMode`, and a combined pytest fixture, remain
  Milestone 4 work.

## Milestone 4 — Hybrid validation wiring + Database layer ✅ done

- `framework/database`: `ConnectionFactory`/`ConnectionPoolManager`/
  `DatabaseManager` (SQLAlchemy engine per dialect — Oracle/PostgreSQL/
  MySQL/SQL Server/SQLite, connection pooling from `DatabaseConfig`),
  `QueryExecutor`/`TransactionManager`/`ResultMapper`, a repository per
  domain (`SubscriberRepository`, `TenantRepository`, `NetworkRepository`,
  `SteeringRepository`, `AuditRepository`, `AlarmRepository`,
  `SystemRepository`) built on raw SQL organized by domain
  (`framework/database/queries`), `UnitOfWork` for multi-repository
  transactions, `DataComparator` + 6 domain validators for DB-vs-Expected/
  API/UI comparison, Allure telemetry + structured audit logging, and
  `SeedManager`/`CleanupManager`/`SchemaManager` for test data.
- `ValidationFacade` (`framework/hybrid`): dispatches `verify_api`/
  `verify_database` calls based on `ValidationMode`
  (`ui_only`/`ui_api`/`ui_database`/`ui_api_database`) from
  `config/environments/<env>.yaml`/`AUTOMATION_VALIDATION_MODE` — zero test-code
  changes between modes. `validation_facade` and the database repository
  fixtures are registered alongside `driver_fixtures`/`api_fixtures` in
  `tests/conftest.py`.
- Verified against SQLite (default), and — same test code, only
  `AUTOMATION_DB_*` env vars changed — real PostgreSQL 16 and MySQL 8.4 containers
  (`docker-compose.yml`); Oracle/SQL Server share the same code path
  (dialect-mapping unit-tested) but weren't run against a live server in
  this environment. `tests/database/integration` proves the hybrid facade
  end-to-end against three real backends: the-internet.herokuapp.com (UI),
  dummyjson.com (API), and the demo schema (DB).
- Full detail: [DatabaseFramework.md](DatabaseFramework.md),
  [HybridValidation.md](HybridValidation.md),
  [RepositoryPattern.md](RepositoryPattern.md),
  [DatabaseConfiguration.md](DatabaseConfiguration.md),
  [DatabaseBestPractices.md](DatabaseBestPractices.md).
- Not done (left for when a real target application/database exists): the
  demo schema (`tenants`/`networks`/`subscribers`/`steering_zones`/
  `audit_log`/`alarms`/`system_config`) is a representative schema proving
  framework capability, not any specific customer's real database schema.
  Wiring Subscriber/Steering Management end-to-end across a real UI + real
  API + real DB is future work once real access exists for all three.

## Milestone 5 — Test Data Management Framework ✅ done

- `framework/testdata`: Builder pattern (`BaseBuilder` + 8 domain builders —
  Tenant/Network/Subscriber/SteeringRule/Alarm/SIM/Billing/User), Factory
  pattern on top of the builders, a 10-scenario `ScenarioLibrary`
  (New/Roaming/Blocked Subscriber, Premium/Enterprise Customer, Inactive
  SIM, Expired Subscription, Alarm Raised, Network Failure, Billing Error).
- Telecom identifier generators (IMEI/ICCID Luhn-valid, IMSI/MSISDN/PLMN/
  cell ID/tracking area code), deterministic (seeded, repeatable)
  generation, a custom-generator registry.
- Dataset management (`DatasetLoader`: JSON/YAML/CSV/Excel, versioned,
  shared, and file-authored-scenario conventions on top of `data/testdata/`),
  a uniform `DataProvider` interface (DB/API/JSON/CSV/Excel/env), arbitrary-
  path importers/exporters, and a TTL-aware in-memory cache.
- Data validation (schema, format — including Luhn checks, business-rule
  registry, uniqueness, referential integrity), PII masking/redaction,
  Fernet encryption (reusing `framework.database.utilities.secrets`), and
  synthetic bulk generation/anonymization.
- Multi-layer seeding (`DatabaseSeeder`, `ApiSeeder`, `SeedOrchestrator`)
  and cleanup (`CleanupRegistry`, `DatabaseCleanupService`,
  `ApiCleanupService`, `UiCleanupHooks`, `RollbackManager`) — the
  `seeded_scenario` pytest fixture seeds a named scenario's DB-backed
  entities and registers their cleanup in one call.
- Proven end-to-end: `tests/testdata/integration/test_hybrid_tdm_flow.py`
  threads TDM-built data through a real UI action, a real API call
  (dummyjson.com), and a real DB validation, parametrized across all four
  `ValidationMode` values with an **identical test body** — the "no
  hardcoded business data, consume -> validate -> cleanup without
  modifying test logic" requirement, proven against real backends rather
  than just described.
- Full detail: [TestDataFramework.md](TestDataFramework.md),
  [BuilderPattern.md](BuilderPattern.md),
  [ScenarioLibrary.md](ScenarioLibrary.md),
  [DatasetManagement.md](DatasetManagement.md),
  [SyntheticData.md](SyntheticData.md),
  [CleanupStrategy.md](CleanupStrategy.md),
  [BestPractices.md](BestPractices.md).

## Milestone 6 — Real customer application modules (per-customer, evidence-driven)

This framework ships with generic, customer-agnostic sample modules only
(Milestone 3's 6 skeleton modules, plus Subscriber Management against the
public herokuapp demo target). Building real Page Objects for a specific
customer's real application is intentionally **out of scope for the
framework itself** — it happens in a downstream project/fork that:

1. Records real Playwright codegen (or captures real DOM/HAR evidence)
   against that customer's actual application.
2. Builds Page Objects only for screens with real evidence — never
   extrapolated from a module name or screenshot alone (see
   [BestPractices.md](BestPractices.md)).
3. Reuses this framework's existing components/services/validation layers
   rather than duplicating them.

The 6 Milestone-3 skeleton modules remain real, working code — a template
for that per-customer workflow, not a target to keep extending here.

## Milestone 7 — Performance & Security packages
- `framework/performance`: load-shaping helpers, timing assertions,
  integration point for a load-generation tool.
- `framework/security`: auth/session tests, header checks, injection probes
  against the API layer (`framework/api` already gives this a real client to
  build on).

## Milestone 8 — AI-assisted testing
- `framework/ai`: self-healing locator fallback chain (falling back through
  the same testid > role > label > css > xpath priority `Locators` already
  encodes), LLM-assisted root-cause summaries of failures, LLM client
  abstraction (OpenAI/Claude/Gemini), feature-flagged per environment
  (`feature_flags.self_healing_locators`, etc. already in the config schema).

## Milestone 9 — Contract, messaging, and streaming protocols
- SOAP, GraphQL, Kafka, RabbitMQ, gRPC, WebSocket client scaffolds — likely
  as siblings to `framework/api/client` (e.g. `framework/api/client/grpc_client.py`)
  reusing the same auth/middleware/validator layers where it makes sense,
  added as real integrations require them rather than speculatively.

## Deliberately deferred until needed
- Remaining docs (`CodingStandards.md`, `CI-CD.md`, `ContributionGuide.md`,
  `FAQ.md`) — written once there's enough real usage/history to document
  accurately, rather than as placeholders now.
- Committed (cross-run, cross-platform) visual-testing baselines for a real
  target application's screens — `tests/visual/` today uses per-run baselines specifically to
  avoid macOS-vs-Linux-CI font-rendering false positives; a team wanting
  stable baselines should generate and commit them from the actual CI
  platform, not a dev machine.
