# Existing Framework Sync

`framework.sync` — optional (`feature_flags.framework_sync`), read-only by
default. See [ModularArchitecture.md](ModularArchitecture.md) for how this
fits alongside Discovery and AI.

## Workflow

```
Existing Repository (local dir / .zip / git URL)
          │
          ▼
Repository Analyzer (static analysis only — never executes anything)
          │
          ▼
Framework Discovery Model (RepositoryAnalysis — language, detected
frameworks, structure, findings)
          │
          ▼
Compatibility Mapping (FrameworkAdapter per technology + a real,
inspectable compatibility ratio)
          │
          ▼
Target Framework Model (this framework's own architecture — Page
Objects/services/repositories)
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

## Framework adapters

`FrameworkAdapter` is the extension point for recognizing a new
technology — each adapter detects its own fingerprint in the analyzed
file contents and reports a `SupportLevel` (`supported` /
`partially_supported` / `requires_manual_review`) plus migration notes.
Shipped adapters: `PlaywrightAdapter`, `SeleniumAdapter`, `CypressAdapter`,
`PytestAdapter`, `JUnitAdapter`, `TestNGAdapter`. Add a new one rather than
hardcoding detection logic elsewhere.

## Compatibility scoring

`compute_compatibility_report()` computes
`compatibility_ratio = supported_count / total_detected` directly from
the adapters' `support_level` results — a transparent, inspectable
number, not a fabricated score. An empty detection (`total_detected == 0`)
is reported as "manual review required," not a 0% score.

## Safety

- Analysis never modifies the source repository.
- Findings (hardcoded credentials/URLs) report file + line + category —
  never the matched secret value.
- `scaffold` only ever writes into `--output-dir` (default `generated/`,
  gitignored).
- Nothing is auto-applied to this framework or to the analyzed repository.
