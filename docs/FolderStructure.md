# Folder Structure

```
enterprise-automation-framework/
├── framework/                  # everything reusable — no test logic lives here
│   ├── core/                   # BaseTest and other test-level scaffolding
│   ├── config/                 # EnvironmentSettings models + loader (Pydantic Settings)
│   ├── pages/                  # Page Object Model
│   │   ├── login_page.py, dashboard_page.py   # Authentication / Dashboard modules (Milestone 1)
│   │   ├── subscriber_management/             # real, live-verified (Milestone 3)
│   │   ├── policy_management/ alarm_management/ reports/ administration/
│   │   │   audit_logs/ user_management/       # real code, skipped example tests (no real target app)
│   │   └── each module/: page.py, assertions.py, test_data.py, __init__.py
│   ├── components/             # Page Component Model — 14 reusable widgets (Milestone 3)
│   │   ├── header, sidebar, top_navigation, breadcrumb            (chrome/navigation)
│   │   ├── table, pagination, grid                                (data display)
│   │   ├── modal, confirmation_dialog, notification               (overlays)
│   │   └── search_box, date_picker, dropdown, tree_view            (input widgets)
│   ├── navigation/              # AppNavigator — composes nav components into go_to_module()
│   ├── workflows/               # LoginWorkflow, LogoutWorkflow, SubscriberSearchWorkflow,
│   │                             #   PolicyCreationWorkflow, UserCreationWorkflow
│   ├── waits/                   # WaitManager — every non-trivial wait condition, no hardcoded sleeps
│   ├── locators/                # Locators — testid > role > aria-label > css > xpath priority strategy
│   ├── accessibility/           # AccessibilityChecker (axe-core via axe-playwright-python)
│   ├── visual/                  # VisualComparator — screenshot-diff visual regression (Pillow)
│   ├── drivers/                # BrowserFactory + DriverManager (Playwright lifecycle)
│   ├── api/                    # API automation module — implemented (Milestone 2)
│   │   ├── client/             # ApiClient (GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS over httpx)
│   │   ├── auth/                # Pluggable httpx.Auth strategies + AuthFactory
│   │   ├── builders/             # RequestBuilder (fluent) -> RequestSpec
│   │   ├── validators/            # ResponseValidator (fluent) + JSON path resolver
│   │   ├── schemas/                # *.json JSON Schema files + SchemaRegistry
│   │   ├── endpoints/               # Endpoints — centralized path templates
│   │   ├── models/                   # Pydantic request/response models
│   │   ├── services/                  # AuthService/UserService/ApiValidator (domain facades)
│   │   ├── middleware/                 # httpx event hooks: correlation ID, logging, Allure
│   │   ├── utilities/                   # small cross-cutting helpers
│   │   ├── exceptions/                   # API-specific exception hierarchy
│   │   ├── fixtures/                      # pytest fixtures: settings -> ApiClient -> services
│   │   └── constants/                      # header names, content types, retry policy
│   ├── database/                # Database validation layer — implemented (Milestone 4)
│   │   ├── connection/           # ConnectionFactory, ConnectionPoolManager, DatabaseManager
│   │   ├── drivers/                # dialect_registry — DbDialect -> SQLAlchemy driver/port/pip-package
│   │   ├── queries/                 # raw SQL by domain (tenant/network/subscriber/steering/audit/alarm/system)
│   │   ├── models/                   # frozen dataclasses, one per domain
│   │   ├── repositories/               # BaseRepository + 7 domain repositories (Repository pattern)
│   │   ├── services/                    # UnitOfWork, SeedManager
│   │   ├── validators/                   # DatabaseValidator + 6 domain validators (DB vs Expected/API/UI)
│   │   ├── utilities/                     # QueryExecutor, TransactionManager, ResultMapper,
│   │   │                                   #   DataComparator, SchemaManager, CleanupManager, CredentialResolver
│   │   ├── fixtures/                       # pytest fixtures wiring all of the above
│   │   ├── telemetry/                       # Allure attachment helpers (SQL/timing/rows/comparisons)
│   │   ├── audit/                            # AuditLogger — structured logging of DB activity
│   │   ├── exceptions/                        # DB-specific exception hierarchy
│   │   ├── constants/                          # dialect/driver/pool defaults
│   │   └── enums/                               # DbDialect, TransactionMode, IsolationLevel
│   ├── hybrid/                  # ValidationFacade + fixtures — UI/API/DB dispatch by ValidationMode (Milestone 4)
│   ├── testdata/                # Test Data Management platform — implemented (Milestone 5)
│   │   ├── generators/            # RandomData extension, TelecomIdentifierGenerator (IMEI/IMSI/ICCID/MSISDN,
│   │   │                          #   Luhn-valid), DeterministicGenerator, CustomGeneratorRegistry
│   │   ├── builders/               # BaseBuilder + 8 domain builders (Tenant/Network/Subscriber/SteeringRule/
│   │   │                           #   Alarm/SIM/Billing/User) — fluent, produce framework.database.models directly
│   │   ├── factories/               # Canned Factory-Method instances built on the builders
│   │   ├── scenarios/                # ScenarioLibrary — 10 named, reusable business scenarios
│   │   ├── datasets/                  # DatasetLoader (JSON/YAML/CSV/Excel, versioned/shared/scenario files)
│   │   ├── providers/                  # DataProvider — DB/API/JSON/CSV/Excel/env, one fetch(key) interface
│   │   ├── validators/                  # Schema, format (incl. Luhn), business-rule, uniqueness, relationship
│   │   ├── masking/                      # DataMasker, PII field registry, Fernet encryption (TestDataEncryption)
│   │   ├── synthetic/                     # SyntheticDatasetGenerator (bulk), Anonymizer
│   │   ├── importers/ exporters/           # arbitrary-path CSV/JSON/Excel import/export
│   │   ├── cache/                           # TTL-aware in-memory DataCache
│   │   ├── seed/                             # DatabaseSeeder, ApiSeeder, SeedOrchestrator
│   │   ├── cleanup/                           # CleanupRegistry, DatabaseCleanupService, ApiCleanupService,
│   │   │                                      #   UiCleanupHooks, RollbackManager
│   │   └── fixtures/                           # pytest fixtures: seeded_scenario, load_dataset, build_scenario,
│   │                                            #   cleanup_registry, database_seeder/cleanup_service
│   ├── services/
│   │   └── backend/             # (reserved) backend/service-layer validation clients
│   ├── utilities/               # screenshots, files, dates, random data (Faker), test-data loader
│   │                             #   (JSON/CSV/Excel/environment-specific — Milestone 3)
│   ├── logger/                  # Loguru setup, get_logger(component)
│   ├── reporting/                # (reserved) Allure environment/category helpers
│   ├── fixtures/                  # pytest fixtures (driver, settings) + hooks
│   ├── assertions/                 # Assert (hard), SoftAssert (multi-failure), UIAssert (element-level)
│   ├── exceptions/                  # framework-wide exception hierarchy
│   ├── retry/                       # @retry_on decorator (Tenacity)
│   ├── security/                      # (reserved) security test helpers
│   ├── performance/                    # (reserved) performance test helpers
│   ├── ai/                              # optional AI provider abstraction (implemented — see
│   │                                     #   docs/ModularArchitecture.md); self-healing locators/
│   │                                     #   RCA are future extensions, not built (docs/FutureRoadmap.md)
│   ├── integrations/                     # (reserved) outbound notifications (Slack/Jira/etc.)
│   ├── validators/                        # (reserved) business-rule validators (UI-layer, distinct from
│   │                                        #   framework/database/validators [DB/API/UI cross-layer] and
│   │                                        #   framework/testdata/validators [test-data shape/format/rules])
│   ├── models/                             # (reserved) shared Pydantic domain models (UI-layer)
│   ├── constants/                           # Timeouts and other fixed values
│   └── enums/                                # Environment, BrowserType, ValidationMode
│
├── tests/                      # test code only — imports framework/, never Playwright/httpx directly
│   ├── smoke/                  # UI: fast critical-path checks
│   ├── negative/               # UI: invalid-input / error-path checks (Milestone 3)
│   ├── accessibility/          # UI: axe-core scans (Milestone 3)
│   ├── visual/                 # UI: screenshot-diff regression (Milestone 3)
│   ├── sanity/                 # UI: post-deploy checks (planned)
│   ├── regression/             # UI: full regression suite (planned)
│   ├── e2e/                    # UI: cross-module business flows
│   │   ├── subscriber_management/   # real, passing (Milestone 3)
│   │   └── policy_management/ alarm_management/ reports/ administration/
│   │       audit_logs/ user_management/   # real code, pytest.mark.skip'd (no real target app)
│   ├── api/                    # API automation tests — implemented (Milestone 2)
│   │   ├── smoke/              # live auth smoke tests (dummyjson.com)
│   │   ├── regression/         # live CRUD/negative tests + offline unit tests (httpx.MockTransport)
│   │   ├── sanity/             # (planned)
│   │   └── integration/        # (planned)
│   ├── database/                # Database + hybrid validation tests — implemented (Milestone 4)
│   │   ├── smoke/               # connectivity/health-check checks
│   │   ├── regression/          # connection factory, query executor, transactions, repositories,
│   │   │                        #   unit of work, comparison, validators, seed/cleanup
│   │   └── integration/         # hybrid (UI+API+DB) tests, all 4 ValidationMode values
│   ├── testdata/                 # Test Data Management tests — implemented (Milestone 5)
│   │   ├── unit/                 # generators, builders, factories, scenarios, providers, datasets,
│   │   │                         #   validators, masking, synthetic, importers/exporters, cache — no DB/network
│   │   └── integration/          # seed/cleanup + fixtures against a real DB; hybrid TDM->UI/API/DB flow
│   ├── backend/ performance/ security/   # (planned, per validation layer)
│   └── conftest.py             # registers driver_fixtures + api_fixtures + database_fixtures +
│                                #   hybrid.fixtures + testdata_fixtures as plugins
│
├── config/environments/        # dev.yaml, qa.yaml, uat.yaml, preprod.yaml, production.yaml
├── data/testdata/               # JSON/CSV/Excel/YAML test data files — per-module (Milestone 3),
│                                 #   plus shared/, scenarios/ conventions (Milestone 5)
├── artifacts/                   # screenshots/videos/traces/har/visual_baselines/visual_diffs — gitignored
├── reports/                     # allure-results/, allure-report/ — gitignored
├── logs/                        # rotating execution.log — gitignored
├── docker/Dockerfile
├── docker-compose.yml
├── scripts/                     # (reserved) maintenance/one-off scripts
├── docs/                        # this file and its siblings
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml               # Poetry deps + Black/Ruff/MyPy/Bandit/Coverage config
└── .env.example
```

Directories marked "(reserved)" or "(planned)" exist with an `__init__.py`
today so import paths are stable, but have no implementation yet — see
[FutureRoadmap.md](FutureRoadmap.md) for build order. `framework/api/` and
`tests/api/` were fully implemented in Milestone 2 (see
[APIFramework.md](APIFramework.md)); the UI automation layers listed above
(components, navigation, workflows, waits, locators, accessibility, visual,
sample module skeletons) were fully implemented in Milestone 3 (see
[Architecture.md](Architecture.md#ui-automation-architecture-milestone-3));
`framework/database/`, `framework/hybrid/`, and `tests/database/` were fully
implemented in Milestone 4 (see [DatabaseFramework.md](DatabaseFramework.md)
and [HybridValidation.md](HybridValidation.md)); `framework/testdata/` and
`tests/testdata/` were fully implemented in Milestone 5 (see
[TestDataFramework.md](TestDataFramework.md)).
