# Troubleshooting

**`ScopeMismatch` error mentioning a session-scoped `base_url` fixture**
Caused by the third-party `pytest-playwright` plugin's own `base_url` fixture
colliding with this framework's custom one. This framework does not depend on
`pytest-playwright` (it has its own `DriverManager`) — if it or its
transitive dependency `pytest-base-url` end up installed anyway (e.g. an IDE
auto-added it), remove them: `pip uninstall pytest-playwright pytest-base-url`.

**MyPy passes but the module fails to import at runtime with `ImportError: cannot import name 'X' from 'loguru'`**
Some third-party packages (Loguru included) only expose certain names in their
`.pyi` type stubs, not at runtime. Guard stub-only imports with
`if TYPE_CHECKING:` and use `from __future__ import annotations` so the
annotation itself is never evaluated at import time.

**Bandit flags a CSS selector like `"#password"` as B105 (hardcoded password)**
False positive — Bandit's heuristic matches the substring "password" in any
string literal. Suppress with `# nosec B105` and a short comment explaining
why, rather than disabling the rule project-wide.

**`poetry install` seems to install/uninstall Poetry itself**
If `poetry config virtualenvs.create false` is set (installing directly into
an already-active venv rather than a Poetry-managed one) and Poetry itself
was `pip install`-ed into that same venv, `poetry install --sync` may prune
Poetry as an "extraneous" package since it isn't a project dependency. Install
Poetry once via `pipx install poetry` instead, outside any project venv.

**Playwright browser launch fails in Docker/CI with missing system libraries**
Use the `mcr.microsoft.com/playwright/python` base image (already the base
for `docker/Dockerfile`) or run `playwright install --with-deps` — plain
`playwright install` only fetches browser binaries, not their OS-level deps.

**A test passes locally but artifacts (screenshot/trace) aren't in `artifacts/` after a CI failure**
Artifacts are only written on failure by design (`DriverManager.finalize`).
If a test is flaky and passes on retry, no artifacts are kept for the failed
attempt — check the CI job's console log for the failure output instead, or
temporarily set `screenshot_on_failure`/`trace_on_failure` and force the
assertion to fail while debugging.
