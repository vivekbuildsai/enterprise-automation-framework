# Modular Architecture

This framework is a set of independent capabilities, not one monolithic
system. Core automation works completely on its own; everything else is
opt-in, gated by `feature_flags` in `config/environments/*.yaml`
(`framework.config.models.FeatureFlags`), and lives in its own
importable package that core code never imports from.

```
                         AUTOMATION PLATFORM
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
          CORE ENGINE        DISCOVERY ENGINE     FRAMEWORK SYNC
     (pages/api/database/    (framework.discovery)  (framework.sync)
      network/reporting)
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  ▼
                           COMMON DATA MODEL
                    (Pydantic reports: DiscoveryReport,
                     RepositoryAnalysis — JSON, inspectable)
                                  │
                                  ▼
                         OPTIONAL AI LAYER
                            (framework.ai)
                                  │
                                  ▼
                     HUMAN REVIEW / APPROVAL
                  (generated/ output, never auto-applied)
                                  │
                                  ▼
                       AUTOMATION ARTIFACTS
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
                UI               API               DB
                 │                │                │
                 └────────────────┼────────────────┘
                                  ▼
                         VALIDATION ENGINE
                                  │
                                  ▼
                       REPORTING / EVIDENCE
```

## Capability matrix

| Capability | Package | Optional? | Feature flag |
|---|---|---|---|
| UI automation | `framework.pages`/`framework.components` | No — core | n/a |
| API automation | `framework.api` | No — core | `api_validation` |
| Database validation | `framework.database` | No — core | `database_validation` |
| Network/JSON-RPC interception | `framework.network` | No — core | `network_interception` (default `true`) |
| Reporting | Allure/HTML (pytest plugins) | No — core | n/a |
| Application Discovery | `framework.discovery` | **Yes** | `discovery` |
| Existing Framework Sync | `framework.sync` | **Yes** | `framework_sync` |
| AI Assistance | `framework.ai` | **Yes** | `ai_assistance` |
| Code generation (discovery/sync scaffolding) | `framework.discovery.code_generator` / `framework.sync.scaffold` | **Yes** | `code_generation` |

**The rule that makes this true, not aspirational:** `framework.pages`,
`framework.api`, `framework.database`, `framework.network`, and
`framework.reporting`/`framework.assertions` contain zero imports of
`framework.discovery`, `framework.sync`, or `framework.ai` — verified by
`grep -rl "framework\.\(discovery\|sync\|ai\)" framework/pages framework/api framework/database framework/network` returning nothing. Feature
flags gate CLI entry points and call sites that choose to check them; they
don't gate imports, because the packages are already structurally
separate.

## Feature combination matrix

| Customer | Core | Discovery | Framework Sync | AI |
|---|---|---|---|---|
| A | ✓ | | | |
| B | ✓ | ✓ | | |
| C | ✓ | | ✓ | |
| D | ✓ | | | ✓ |
| E | ✓ | ✓ | | ✓ |
| F | ✓ | | ✓ | ✓ |
| G | ✓ | ✓ | ✓ | ✓ |

No combination requires another optional capability — Discovery, Framework
Sync, and AI can each be enabled or left off independently.

## Core Automation

- **What it does**: UI (Playwright), API, and database test automation,
  plus network/JSON-RPC capture and Allure/HTML reporting.
- **When to use it**: always — this is the framework.
- **What it requires**: nothing beyond `poetry install` and a target
  application/API/database to point at.
- **What it produces**: test results, Allure evidence, validation reports.
- **Security considerations**: standard — credentials via `.env`/env vars,
  never committed (see FRAMEWORK_MAINTENANCE_GUIDE.md).
- **Optional?**: No.

## Application Discovery (`framework.discovery`)

- **What it does**: passive UI element discovery (only emits locators
  with real, stable evidence — test-id/role+name/id/name, never a guess),
  OpenAPI-spec-based API endpoint discovery, and read-only database schema
  reflection. Produces `DiscoveryReport` JSON + optional Page
  Object/domain-model code skeletons (`generated/`, human-reviewed).
- **When to use it**: onboarding a new target application, to speed up
  building the first Page Objects/domain models.
- **What it requires**: authorized access to the target UI (a real
  Playwright `Page`), an OpenAPI spec file for API discovery, or a
  configured database connection for schema reflection — see the
  `framework/discovery/*.py` module docstrings and the README's
  "Extending the framework" section for the full API.
- **What it produces**: `discovery_report.json` + optional generated code
  under `generated/`.
- **Security considerations**: UI discovery never submits forms or
  attempts login/credential guessing — look-don't-touch. Only run it
  against applications you're authorized to test.
- **Optional?**: Yes — `feature_flags.discovery`.

## Existing Framework Sync (`framework.sync`)

- **What it does**: read-only analysis of an existing automation
  repository (local directory, `.zip`, or git URL) — language/test-runner/
  automation-library detection via `FrameworkAdapter`s (Playwright/
  Selenium/Cypress/pytest/JUnit/TestNG), structural counts, and a
  hardcoded-credential/URL scan (values never logged). Produces a
  `RepositoryAnalysis` + a defensible `CompatibilityReport` (a real ratio
  of detected-technology support levels, never a fabricated score).
  Mode 2 (`scaffold`) generates a migration worksheet (Markdown, not
  source code).
- **When to use it**: assessing an existing test automation repo before
  deciding how (or whether) to port it onto this framework.
- **What it requires**: read access to the source (a local path, `.zip`
  file, or a git URL your own git credentials can already clone).
- **What it produces**: `repository_analysis.json`, optionally
  `generated/MIGRATION_WORKSHEET.md`.
- **Security considerations**: `ZipArchiveSource` rejects path-traversal
  archive members (zip-slip protected) and never executes archive
  contents. `GitRepositorySource` never requests, stores, or logs a
  credential — it relies entirely on credentials already configured
  outside this framework (SSH agent / git credential manager). Analysis
  never modifies the source repository.
- **Modes implemented**: Mode 1 (ANALYZE) and Mode 2 (SCAFFOLD). **Mode 3
  (MIGRATE — generating translated source) and Mode 4 (SYNC — diff-driven
  re-application) are intentionally NOT implemented** — genuine
  source-to-source translation between automation frameworks is a much
  larger, framework-pair-specific effort than a generic tool can safely
  claim to do automatically; `SyncMode` models them as the extension
  point for that future work, not as delivered functionality.
- **Optional?**: Yes — `feature_flags.framework_sync`.

## AI Assistance (`framework.ai`)

- **What it does**: an optional, pluggable `AIProvider` layer.
  `DisabledProvider` (the default) never makes a network call.
  `OpenAICompatibleProvider` works against any endpoint speaking the
  OpenAI chat-completions API shape — cloud OpenAI, Azure OpenAI, or a
  self-hosted/local server (Ollama, vLLM, LM Studio, an enterprise
  inference gateway) — without hardcoding a vendor.
- **When to use it**: enrich discovery/sync output with suggestions
  (e.g., "does this look like a login button?") — always a
  recommendation, never an automatic action.
- **What it requires**: `ai.enabled=true` + `ai.provider`/`ai.endpoint`/
  `ai.model` in `config/environments/*.yaml` (or `AUTOMATION_AI_*` env
  vars). No configuration = `DisabledProvider`, and the framework runs
  identically either way.
- **What it produces**: `AIRecommendation` objects, each carrying a
  `RecommendationConfidence` (`discovered` / `inferred` / `ai_suggested` /
  `manually_confirmed`) — output is never silently treated as a fact.
- **Security considerations**: `ai.api_key` must come from an environment
  variable, never a committed literal. `redact_secrets()` strips anything
  that looks like a password/API key/token/Bearer header from a prompt
  before it's sent. On any HTTP error, timeout, or malformed response,
  the provider returns a clearly-labeled fallback recommendation instead
  of raising — AI is an enhancement layer, never a single point of
  failure for core execution.
- **Optional?**: Yes — `feature_flags.ai_assistance`.

## CLI reference

`python -m framework <command>` is the single entry point; each command
dispatches to its own independently-runnable CLI (`python -m
framework.discovery ...` / `python -m framework.sync ...` still work
directly too — `framework.cli` is a thin dispatcher, not new logic).

```bash
# Discovery (optional — feature_flags.discovery)
poetry run python -m framework discover ui <url> --report report.json
poetry run python -m framework discover api <openapi.json> --report report.json
poetry run python -m framework discover db <db_key> --env dev --report report.json
poetry run python -m framework discover generate --report report.json --output-dir generated/
poetry run python -m framework discover recommend --report report.json --env dev \
    --output recommendations.json   # optional AI layer, see below

# Framework Sync (optional — feature_flags.framework_sync)
poetry run python -m framework sync analyze <local-dir|.zip|git-url> --report analysis.json
poetry run python -m framework sync scaffold --report analysis.json --output-dir generated/
poetry run python -m framework sync diff <before.json> <after.json>
poetry run python -m framework sync recommend --report analysis.json --env dev \
    --output mapping_recommendations.json   # optional AI layer, see below
poetry run python -m framework sync scaffold --report analysis.json \
    --recommendations mapping_recommendations.json   # folds them into the worksheet

# Core — always available, no feature flag
poetry run python -m framework validate --expected expected.json --actual actual.json
poetry run python -m framework report generate   # wraps the `allure` CLI
poetry run python -m framework report open
```

## AI-assisted recommendation pipeline (Discovery & Framework Sync)

Both `discover recommend` and `sync recommend` implement the same shape:

```
Discovery / Repository Analysis
          │
          ▼
   Discovery Model (DiscoveryReport / RepositoryAnalysis — unchanged)
          │
          ▼
   Optional AI Provider (framework.ai.get_provider(settings.ai))
          │
          ▼
   Recommendation (AIRecommendation: text + provider)
          │
          ▼
   RecommendationConfidence (discovered / ai_suggested, see below)
          │
          ▼
   Human Review (a plain JSON file — recommendations.json /
                 mapping_recommendations.json)
          │
          ▼
   Approved Discovery Model — a human decides what to act on; nothing
   here writes to `--report`, to `generated/`, or to any source file.
```

- `framework.discovery.ai_recommendations.recommend_for_report()` asks the
  provider for a suggested method name/description per discovered
  element and returns a list of `ElementRecommendation` — never mutates
  the `DiscoveryReport`.
- `framework.sync.ai_recommendations.recommend_mappings()` asks the
  provider for a migration suggestion per detected technology and
  returns a list of `MappingRecommendation` — never mutates the
  `RepositoryAnalysis`. Optionally fed into
  `generate_migration_worksheet(analysis, ai_recommendations=...)`, which
  appends them as a separate, clearly-labeled "unverified — human review
  required" section; the deterministic content is unaffected either way.
- Both work identically with AI disabled: `DisabledProvider` still
  produces one recommendation per item, each with
  `RecommendationConfidence.DISCOVERED` ("no AI opinion available")
  instead of `AI_SUGGESTED` — Discovery and Sync run to completion with
  or without AI configured.
- **AI never silently modifies source code.** Every recommendation lands
  in its own output file; folding one into a worksheet still only
  produces a Markdown file under `generated/` — nothing is written back
  to `--report`, to a generated Page Object/domain model, or to the
  analyzed repository.

## Honest positioning

This is an **assisted automation framework**, not a claim of "fully
autonomous automation." Discovery only emits evidence it directly
observed. Sync's compatibility numbers are real ratios of detected
technologies, not fabricated scores. AI output is always a labeled
recommendation requiring review, never something the framework acts on by
itself. Every artifact these optional capabilities produce is written to
`generated/` (gitignored, human-reviewed) — nothing is auto-applied to the
framework or to any target repository.
