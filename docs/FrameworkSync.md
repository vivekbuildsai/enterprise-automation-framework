# Multi-Language & Multi-Framework Framework Sync

## New UI extension analysis

Framework Sync can also be the read-only capability inventory for a new UI
added to an already mature automation ecosystem. `python -m framework
extension analyze --framework <existing-path> --url <new-ui-url>` runs
`sync analyze` and shape-only new-UI discovery internally in one command
(saving both intermediate reports too), correlates the two, and produces
an extension report. The report identifies evidence-backed reuse candidates
for existing API, database, authentication, validation, test-data,
reporting, Page Object, and component capabilities; analysis never modifies
either target.

An API endpoint/method match is a likely reuse candidate, while a path/table
name match is deliberately weaker evidence and is reported as an extension or
manual-review candidate. `UNKNOWN` and `MANUAL_REVIEW` are valid outcomes.
The extension report is a review checkpoint on its own — but, unlike a plain
analysis report, it can optionally be turned into a framework-native
scaffold via `python -m framework extension scaffold` (see "Framework-native
scaffolding" below), always behind an explicit `--approve` gate.

`python -m framework.extension analyze` supports four customer choices via
`--mode`, each a strict superset of the previous:

- **Discover only** — run `python -m framework.discovery`/`sync analyze` on
  their own; this CLI is not involved at all.
- **Discover + reuse analysis** (`--mode reuse-analysis`) — UI/API/database
  correlations only.
- **Discover + extension plan** (`--mode extension-plan`, the default) —
  adds the REUSE_EXISTING/EXTEND_EXISTING/CREATE_NEW/UNKNOWN/MANUAL_REVIEW
  extension report and the Test Opportunity Inventory (named, human-reviewed
  testing opportunities — never auto-generated test cases).
- **Discover + optional AI** (`--mode ai-recommendations`) — adds AI
  suggestions, but only for items the deterministic pass left as
  `MANUAL_REVIEW`/`UNKNOWN`; an item already classified REUSE_EXISTING/
  EXTEND_EXISTING/CREATE_NEW never gets one, since there's nothing ambiguous
  left for AI to weigh in on. Gated by `ai.enabled`; deterministic and
  network-free with the default `DisabledProvider`.

Network capture during discovery is shape-only: `DiscoveredNetworkCall`
records method, path, status, and query-parameter/JSON-body **key names**
only — never a header, query value, or body value — so a discovery report
stays safe to persist even against an authenticated session carrying real
customer data.

### Framework-native scaffolding

`python -m framework extension scaffold` turns an extension report into
actual draft source files — but only for items classified `CREATE_NEW`/
`EXTEND_EXISTING`, only in the existing repository's own detected
language/framework/test-runner style (`framework.extension.target`
supports Java+Selenium+TestNG, Java+Selenium+JUnit, Python+pytest+
Playwright, TypeScript+Playwright, and Robot Framework — every other
combination, e.g. C#, falls back to a README-only plan rather than
fabricating code nobody asked for). A `REUSE_EXISTING` item is never
scaffolded, and an already-reusable capability is referenced by name and
source file in a comment, never duplicated as a second implementation
(no second `ApiClient`, `DatabaseManager`, or `DataComparator`).

Two safety mechanisms gate every write:

- **Human approval** — `scaffold` always computes and prints the plan
  (files, reused capabilities, manual-review items); nothing is written
  to disk unless `--approve` is also passed. `--dry-run` always previews,
  even alongside `--approve`.
- **Project-root containment** — `--output-dir` is resolved against
  `framework.project_root.PROJECT_ROOT` and rejected if it would land
  outside it (an accidental absolute path, a `..`-escaping relative path,
  or a page-title-derived filename attempting traversal); a conflicting
  path at the target location fails the *entire* write unless
  `--overwrite` is given — never a silent partial overwrite of customer
  files.

Every generated file carries a `GENERATED SCAFFOLD — REVIEW REQUIRED`
notice plus `TODO` markers wherever a locator/mapping/assertion wasn't
itself confirmed evidence; nothing here is ever labeled production ready.
The manifest (`extension-manifest.json`, written alongside the generated
files) records reused capabilities, newly generated ones, and manual-review
items — never file content, and never a raw captured value.

`framework.sync` — optional (`feature_flags.framework_sync`), read-only by
default. See [ModularArchitecture.md](ModularArchitecture.md) for how this
fits alongside Discovery and AI.

Named deliberately as **"Multi-Language & Multi-Framework"**, not just
"Multi-Language" — this tool understands both *programming languages*
(Java, TypeScript/JavaScript, Python, C#) and *automation
frameworks/DSLs/test runners* (Selenium, Playwright, Cypress, WebdriverIO,
TestNG, JUnit, NUnit, xUnit, pytest, **Robot Framework**) as two
independent axes. Robot Framework in particular is a keyword-driven
automation DSL, not "Python" — it gets its own first-class adapter and
structural model rather than being folded into Python detection (see
"Robot Framework is first-class" below).

**This is not a transpiler.** No source-to-source translation, no
automatic migration, no execution of anything in the analyzed repository.
The output is analysis, a normalized understanding, and human-reviewed
migration guidance — see "Sync modes" below for exactly what is and isn't
implemented.

## Workflow

```
Existing Repository (local dir / .zip / git URL / file://)
          │
          ▼
Language Detection + Framework/Runner/DSL Detection
    (file extensions, dependency files, structural evidence —
     never execution; see "Detection mechanism" below)
          │
          ▼
Language/Framework Adapters (FrameworkAdapter per technology)
          │
          ▼
Normalized Analysis (RepositoryAnalysis — language breakdown, detected
frameworks, structure, Robot Framework structure when applicable, findings)
          │
          ▼
Compatibility Mapping (a real, inspectable compatibility ratio) +
Cross-Language Mapping (concept-level migration guidance)
          │
          ▼
Migration Worksheet (human-reviewed, generated — never source code)
          │
          ▼
Optional AI Recommendations (never authoritative)
```

## Input sources

| Source | Class | Notes |
|---|---|---|
| Local directory | `LocalDirectorySource` | Never copies or modifies the caller's directory. |
| `.zip` archive | `ZipArchiveSource` | Secure extraction — rejects any member whose resolved path would land outside the extraction directory (zip-slip protection). Never executes archive contents. |
| Git URL | `GitRepositorySource` | `git clone --depth 1 <url>` — works for GitHub/GitLab/Bitbucket/self-hosted/local paths. Relies entirely on credentials already configured outside this framework (SSH agent / git credential manager); never requests, stores, or logs one. |

GitHub's own API is deliberately not used — `git clone` already covers
"a GitHub repository URL" for public repos without needing a token, and
for private repos the caller's own git setup is the right place for
credentials, not this framework.

## Sync modes

| Mode | Status | What it does |
|---|---|---|
| 1 — ANALYZE | **Implemented** | Read-only: language/framework/test-runner detection, structural counts, hardcoded-credential/URL findings. No source modification. |
| 2 — SCAFFOLD | **Implemented (minimal)** | Generates `generated/MIGRATION_WORKSHEET.md` — a human-readable plan (detected technologies + notes + findings). Never generates or transforms source code. |
| 3 — MIGRATE | **Not implemented** | Would generate translated source (e.g. Selenium → Playwright). Modeled in `SyncMode.MIGRATE` as the extension point; not delivered because genuine source-to-source translation between automation frameworks is a much larger, framework-pair-specific effort than this tool can safely automate. |
| 4 — SYNC | **Not implemented** | Would apply a diff-driven re-synchronization against an existing target. `diff_analyses()` (the read-only comparison half) is implemented; the "apply" half is not. |

## Existing customer test inventory

The governing product principle: a customer with hundreds or thousands of
already-working tests is never assumed to want them rewritten. This tool
answers, in order — **what do you already have?** → **how well do we
understand it?** → **what can be reused?** → **what should be
migrated?** → only if explicitly requested, **what can we scaffold?**

`analyze` never counts a source file as a test merely because it exists.
Test-level (not file-level) extraction (`framework.sync.test_inventory`)
requires real framework-specific evidence per technology:

| Technology | Evidence required |
|---|---|
| Java + TestNG/JUnit | An `@Test`/`@Test(...)` annotation directly above a method |
| Python + pytest | A `def test_*` function, or a `test_*` method inside a `class Test*` |
| TypeScript/JavaScript + Playwright | A `test(...)` call (with its enclosing `test.describe(...)`, if any) |
| Cypress | An `it(...)` call (with its enclosing `describe(...)`, if any) |
| Robot Framework | A `*** Test Cases ***` entry |

Each extracted `Test` carries a stable `identifier`
(`<source file>::<class/describe name>::<test name>`) so every later
recommendation traces back to its exact original source — see "Migration
traceability" below. Category (UI/API/Database/UI+API/.../Smoke/
Regression/Integration/Unit/End-to-End) is assigned only from real
evidence — an explicit tag/marker/group first, a same-file
technology-import combination second, `UNKNOWN` otherwise; never
fabricated.

The result is rendered as an **EXISTING AUTOMATION INVENTORY** block
(`framework.sync.test_inventory.format_inventory`) — the first thing
both `analyze`'s console output and the migration worksheet show:

```
EXISTING AUTOMATION INVENTORY

Language:              Java
Framework:             Selenium
Test Runner:           TestNG (via Maven Surefire)
Tests Detected:        3
Test Classes:          2
Test Suites:           1
Tags/Groups:           regression, smoke, ui
Configuration Files:   2
CI Pipeline:           GitHub Actions
Reporting:             Allure
Parallelism:           4
Primary Execution:
    mvn test -Dsurefire.suiteXmlFiles=testng.xml
```

### Execution model

`framework.sync.execution_model.detect_execution_model()` captures how
the customer's suite is *already* run — command, runner, parallelism,
retries, environments, browser, reporting, test selection — purely by
reading known build/CI/runner files (Maven `testng.xml`'s
`parallel`/`thread-count` attributes, `playwright.config.ts`, `pytest.ini`/
`pyproject.toml` `addopts`, GitHub Actions workflow YAML `run:` steps
parsed via PyYAML, `package.json` scripts, README/Makefile/Jenkinsfile
command mentions). **Never executed** — a real customer suite may need
credentials, infrastructure, licenses, or production-like systems this
tool has no business touching. Every field stays `None`/empty unless
backed by a real file; a `.csproj` existing is not evidence a command is
`dotnet test` — file-type convention is never treated as evidence.

### Preservation strategies

| Mode | What it does | How |
|---|---|---|
| A — Preserve | Understand the existing suite without migrating any of it. | The default: `analyze` + `scaffold` with `--scope repository` (the default) still only *analyzes* — nothing is migrated by running it. |
| B — Selective Migration | Guidance for exactly one directory/suite/tag/class/test, leaving every other test untouched. | `scaffold --scope {directory,suite,tag,class,test} --selector <value>` — see "Migration candidate selection" below. |
| C — Full Modernization Analysis | Inventory + technology map + compatibility + migration candidates + risks for the *entire* repository — but never an automatic rewrite of any of it. | `scaffold` with the default `--scope repository` — the "Migration candidates" section covers every detected test, each with its own status/risk, never a bulk "migrate all" action. |

### Migration candidate selection

`framework.sync.migration_candidates.select_migration_candidates()`
filters `analysis.tests` by `MigrationScope`
(`repository`/`directory`/`suite`/`tag`/`class`/`test`) and produces one
`MigrationCandidate` per selected test. A scope other than `repository`
requires a `--selector`; an unmatched selector yields zero candidates
(never an error) — selecting a subset never mutates or implies anything
about the rest of the repository's tests.

### Migration traceability

Every candidate carries full provenance and is concept-level guidance
only — **never** a claim that a conversion happened:

```
Source:
    tests/login/LoginTest.java
    testLoginWithInvalidPassword()

Technology:
    Java / Selenium / TestNG

Target:
    Python / Playwright / pytest

Mapping:
    Conceptually mappable

Risk:
    Medium

Reason:
    Selenium interaction maps to Playwright locator/action model,
    but lifecycle behavior requires manual review.
```

`risk` (`low`/`medium`/`high`/`unknown`) is derived deterministically
from the same `MappingStatus` already computed for the cross-language
mapping table — `directly_reusable` → low, `conceptually_mappable` →
medium, `requires_adaptation` → high — never assigned independently or
guessed. A test whose own technology is already this framework's stack
(pytest, Playwright) is `directly_reusable` with risk `low` — there is
nothing to migrate.

## Framework adapters

`FrameworkAdapter` is the extension point for recognizing a new
technology — each adapter detects its own fingerprint in the analyzed
file contents and reports a `SupportLevel` (`supported` /
`partially_supported` / `requires_manual_review`) plus migration notes.
The core `RepositoryAnalyzer` engine is entirely language-agnostic;
everything language/framework-specific lives in an adapter. Add a new one
rather than hardcoding detection logic elsewhere.

Shipped adapters (`DEFAULT_ADAPTERS`): `PlaywrightAdapter`,
`SeleniumAdapter`, `CypressAdapter`, `WebdriverIOAdapter`, `PytestAdapter`,
`JUnitAdapter`, `TestNGAdapter`, `NUnitAdapter`, `XUnitAdapter`,
`RobotFrameworkAdapter`, `RobotSeleniumLibraryAdapter`,
`RobotBrowserLibraryAdapter`, `RobotRequestsLibraryAdapter`.

### Detection mechanism

Deliberately lightweight — file-extension/dependency-file/regex-token
evidence, never execution, never a full-blown per-language AST parser (a
Java/C#/TypeScript parser dependency would be heavy, slow to keep in
sync with language evolution, and not meaningfully more accurate than
token evidence for *detecting that a technology is used*, as opposed to
translating it). Matching is case-insensitive (`Microsoft.Playwright`,
`OpenQA.Selenium`, `playwright`, `org.openqa.selenium` are all real
evidence for the same underlying technology, just spelled differently
per ecosystem) but suffix-scoped where a bare substring would be too
generic to trust on its own (Robot Framework's `Browser` library name;
C#'s `[Test]` attribute). A capability is only ever marked supported in
this document once detection, real analysis, and a passing test exist for
it — never on file-extension presence alone.

### Robot Framework is first-class

Robot Framework is a keyword-driven automation DSL — `.robot`/`.resource`
files, not Python (or any general-purpose language) source. It gets:

- Its own `language_breakdown`/`primary_language` bucket ("Robot
  Framework"), never folded into "Python."
- Its own structural model, `RobotStructure` (Test Case count, user
  Keyword count, Resource file count, Library names, Variable count,
  Suite/Test Setup/Teardown presence), populated only when `.robot`/
  `.resource` files exist — parsed via `framework.sync.robot_analysis`,
  a small line-based reader of Robot's own `*** Section ***` tabular
  format (deliberately not a full Robot AST/parsing library — the format
  is simple and stable enough that this is sufficient).
- Separate adapters per *library* (`SeleniumLibrary`, `Browser` Library,
  `RequestsLibrary`) rather than one generic "Robot Framework" bucket —
  each implies a different underlying automation technology (WebDriver,
  Playwright-based, HTTP), and each gets its own `SupportLevel`/notes.

## Cross-language mapping

`framework.sync.cross_language_mapping.lookup_cross_language_mappings()`
is a small, curated, evidence-based table — never AI-generated, never
fabricated. It returns a `CrossLanguageMapping` (source technology,
concept, target technology, `MappingStatus`, a concrete manual action)
**only** for technologies/structural elements the analyzer actually
detected; an undetected technology never appears. `MappingStatus` values
(`directly_reusable` / `conceptually_mappable` / `requires_adaptation` /
`not_detected` / `unsupported` / `unknown`) describe a concept-to-concept
relationship — deliberately separate from `SupportLevel`, which grades one
detected technology against this framework's stack as a whole. Every
target technology is this framework's own stack (Playwright/pytest/
`framework.api.ApiClient`) — the one real, actionable migration target
this product can meaningfully guide toward. Rendered in the migration
worksheet's "Cross-language mapping" section whenever any mappings exist.

## Compatibility scoring

`compute_compatibility_report()` computes
`compatibility_ratio = supported_count / total_detected` directly from
the adapters' `support_level` results — a transparent, inspectable
number, not a fabricated score. An empty detection (`total_detected == 0`)
is reported as "manual review required," not a 0% score.

## Support matrix

Only marked ✓ where detection, real structural analysis, and a passing
test exist — see `tests/sync/unit/test_multi_language_detection.py`,
`test_robot_framework.py`, `test_mixed_language.py`,
`test_cross_language_mapping.py`, `test_multi_language_sources.py`, and
the sanitized fixtures under `tests/sync/fixtures/`. "Code Scaffold"
(generating translated source) is **not implemented for any row** —
deliberately out of scope; see "Sync modes" above and "Not implemented"
below.

| Language/DSL | Framework/Library | Detection | Analysis | Cross-Language Mapping | Migration Worksheet | Code Scaffold | AI (optional) |
|---|---|---|---|---|---|---|---|
| Java | Selenium + TestNG | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| Java | Selenium + JUnit | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| TypeScript/JavaScript | Playwright | ✓ | ✓ | — (already this framework's own engine) | ✓ | Not implemented | ✓ |
| TypeScript/JavaScript | Cypress | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| TypeScript/JavaScript | WebdriverIO | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| Python | pytest + Playwright | ✓ | ✓ | — (already this framework's own stack) | ✓ | Not implemented | ✓ |
| Python | Selenium (unittest or other runner) | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| C# | Selenium + NUnit | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| C# | Selenium + xUnit | ✓ | ✓ | ✓ | ✓ | Not implemented | ✓ |
| C# | Playwright | ✓ | ✓ | — (already this framework's own engine) | ✓ | Not implemented | ✓ |
| Robot Framework | SeleniumLibrary | ✓ | ✓ (incl. `RobotStructure`) | ✓ | ✓ | Not implemented | ✓ |
| Robot Framework | Browser Library | ✓ | ✓ (incl. `RobotStructure`) | ✓ | ✓ | Not implemented | ✓ |
| Robot Framework | RequestsLibrary | ✓ | ✓ (incl. `RobotStructure`) | ✓ | ✓ | Not implemented | ✓ |
| *(mixed-language repository)* | *(any combination above)* | ✓ (primary + secondary languages, never collapsed) | ✓ | ✓ | ✓ | Not implemented | ✓ |

## Safety

- Analysis never modifies the source repository.
- Findings (hardcoded credentials/URLs) report file + line + category —
  never the matched secret value.
- `scaffold` only ever writes into `--output-dir` (default `generated/`,
  gitignored).
- Nothing is auto-applied to this framework or to the analyzed repository.
- The customer's existing tests are never executed, renamed, rewritten,
  or deleted, and no dependency of theirs is ever installed — the
  execution model is *captured*, never run (see "Execution model"
  above). A 1,500-test suite may need credentials, infrastructure, or
  licenses this tool has no business touching.
- New UI discovery's network capture is shape-only (method/path/status/key
  names) — no header, query value, or body value is ever persisted in a
  discovery report or sent to an AI provider (see "New UI extension
  analysis" above). `ExtensionItem`/`ExtensionMappingRecommendation`
  evidence is always a deterministic description string, never a raw
  captured value.
- Correlating discovered calls against the capability catalog caches
  compiled endpoint-pattern regexes (`@cache` on `_pattern_regex`) rather
  than recompiling one per (call, capability) pair — measured ~6s -> ~0.1s
  at a 1500-capability, 200-call customer-scale catalog; see
  `tests/performance/test_regression_benchmarks.py`.
