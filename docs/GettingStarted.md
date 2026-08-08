# Getting Started

## Prerequisites

- Python 3.13
- [Poetry](https://python-poetry.org/docs/#installation) (install via `pipx install poetry`, not into a project venv)
- Docker (optional, for containerized runs)

## Setup

```bash
git clone <repo-url> enterprise-automation-framework
cd enterprise-automation-framework

poetry install --no-root
poetry run python -m playwright install chromium firefox webkit

cp .env.example .env
# edit .env with real credentials for the environment you're targeting
```

## Running tests

```bash
# Smoke suite, default (dev) environment, headed off (headless)
poetry run pytest tests/smoke -v

# Negative-path, accessibility, and visual-regression suites
poetry run pytest tests/negative tests/accessibility tests/visual -v

# End-to-end (real: subscriber_management; skipped: the other 6 skeleton modules)
poetry run pytest tests/e2e -v

# Against a specific environment
AUTOMATION_ENV=qa poetry run pytest tests/regression -v

# Parallel execution
poetry run pytest tests/smoke -n auto

# With Allure results
poetry run pytest tests/smoke --alluredir=reports/allure-results
poetry run allure serve reports/allure-results   # requires the Allure CLI locally
```

## Switching browsers / headless

Edit `browser.browser` and `browser.headless` in
`config/environments/<env>.yaml`, or override per-run:

```bash
AUTOMATION_ENV=dev poetry run pytest tests/smoke   # reads browser.* from dev.yaml
```

Supported values: `chromium`, `chrome`, `edge`, `firefox`, `safari` (WebKit
engine — see [Architecture.md](Architecture.md) for why real Safari.app can't
be driven).

## Running via Docker

```bash
docker compose build
docker compose run --rm automation
```

Artifacts (screenshots/traces/videos) and Allure results land in
`./artifacts` and `./reports` on the host via volume mounts.

## Writing a new test

1. Add/extend a Page Object under `framework/pages/` (extend `BasePage`).
   Expose business actions only (`search_subscriber(name)`), never a raw
   locator — see [Architecture.md](Architecture.md#ui-automation-architecture-milestone-3).
2. Reach for a `framework/components/` widget (Table, Modal, Dropdown, ...)
   instead of hand-rolling table/modal interaction logic.
3. Add a test under the right suite in `tests/` (`smoke`, `negative`,
   `accessibility`, `visual`, `sanity`, `regression`, `e2e`, ...), tagged
   with the matching `@pytest.mark`.
4. Use `page` and `settings` fixtures (function/session scoped) — either as
   test parameters directly, or via `framework.core.BaseTest` if you prefer
   class-based suites with `self.page` / `self.settings`.
5. Assert with `framework.assertions.Assert` (plain values), `SoftAssert`
   (collects multiple failures), or `UIAssert` (element-level: visible,
   contains_text, attribute, css, url, title, download_success, ...).

```python
import pytest
from framework.assertions import UIAssert
from framework.pages import LoginPage

@pytest.mark.smoke
def test_example(page, settings):
    login_page = LoginPage(page)
    login_page.base_url = str(settings.ui.base_url)
    login_page.open()
    dashboard = login_page.login(settings.ui.login_username, settings.ui.login_password)
    UIAssert.visible(page.locator("h2"), "Secure area heading")
```

For a multi-page flow, add a `framework/workflows/` class instead of
repeating the page sequence in every test — see `SubscriberSearchWorkflow`
for the pattern.

## Code quality (run before pushing)

```bash
poetry run black framework tests
poetry run ruff check framework tests --fix
poetry run mypy framework
poetry run bandit -r framework -c pyproject.toml
poetry run pre-commit install   # one-time, then runs automatically on commit
```

## Using this framework from your own project

Everything above assumes you're working *inside* this repo. This section is
for the other case: your automation code lives in its **own, separate**
repository, and this framework is just a dependency you install — no
copying framework source, no vendoring.

### How fixtures reach your tests with zero configuration

Normally a pytest plugin needs an explicit `pytest_plugins = [...]` line in
your `conftest.py` before its fixtures (`page`, `settings`, `api_client`,
`db_session`, ...) become visible. This framework avoids that step entirely:
`pyproject.toml` registers every fixture module under the standard
[`pytest11`](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#setuptools-entry-points)
entry-point group. Once the package is installed into your project's
environment (not `poetry install --no-root` — that flag is this repo's own
dev-workflow shortcut and deliberately skips installing its own package
metadata), pytest's plugin auto-discovery finds those entry points and loads
the fixtures automatically for **any** pytest session in that environment.
You'll see it confirmed in pytest's own startup banner
(`plugins: enterprise-automation-framework-0.1.0, ...`). No `conftest.py`
line, no `PYTHONPATH` trick, nothing to remember.

The same "resolve relative to the project you're standing in, not the
package's install location" logic — `framework.project_root` — is the single
resolver every path-sensitive module shares (config, `.env*`, `artifacts/`,
`logs/`, `.auth/`, `data/testdata/`, `config/dashboards/`, visual baselines
and diffs). **Package root** (wherever `framework/` itself is installed —
`site-packages/framework/` once you `pip install` it) and **project root**
(your own automation project, or this repo's own checkout during framework
development) are never the same thing, and this framework never writes
customer-owned runtime data into the former — verified by running a full
suite against an installed package with its `site-packages/framework/`
directory made read-only. Resolution order: an explicit
`AUTOMATION_PROJECT_ROOT` env var, then your current working directory (if
it has `config/environments/`), then this package's own location as a last
resort. Two separate projects using the same installed wheel never share
artifacts, logs, auth state, or visual baselines — each resolves against its
own project root.

### The 10-step customer journey

**1. Install the framework**

With Poetry (recommended — pin to a tag/commit for reproducibility):

```bash
poetry add git+https://github.com/<your-org>/enterprise-automation-framework.git#v0.1.0
```

Or with pip, from a built wheel or directly from git:

```bash
pip install "enterprise-automation-framework @ git+https://github.com/<your-org>/enterprise-automation-framework.git@v0.1.0"
poetry run python -m playwright install chromium firefox webkit  # or: python -m playwright install ...
```

**2. Create your project**

A minimal customer project needs only:

```
my-automation/
├── pyproject.toml          # declares the framework as a dependency (step 1)
├── config/environments/dev.yaml
├── .env
└── tests/
    └── test_first.py
```

No `framework/` directory, no copied source — everything you use is
imported from the installed package (`from framework.pages import BasePage`,
`from framework.api import ApiClient`, ...).

**3. Configure your environment**

Copy the shape of this repo's `config/environments/dev.yaml` (`ui`, `api`,
`database`, `browser`, ... — every value `${VAR:-default}`) into your own
`config/environments/dev.yaml`, and put real values in `.env` /
`.env.dev`. See [Configuration](../README.md#configuration).

**4. Use framework fixtures — nothing to register**

```python
def test_fixtures_are_already_available(page, settings):
    assert settings.environment == "dev"
```

`page` (Playwright), `settings`, `api_client`, `db_session`, and every other
fixture this framework ships are available the moment the package is
installed — see above.

**5. Create your first Page Object**

```python
from framework.pages.base_page import BasePage

class LoginPage(BasePage):
    def login(self, username: str, password: str) -> None:
        self.fill("#username", username)
        self.fill("#password", password)
        self.click("button[type=submit]")
```

**6. Run your first UI test**

```python
def test_login(page, settings):
    login_page = LoginPage(page)
    login_page.base_url = str(settings.ui.base_url)
    login_page.open()
    login_page.login(settings.ui.login_username, settings.ui.login_password)
```

```bash
poetry run pytest tests/test_first.py -v
```

**7. Run a UI + Network validation**

Attach `framework.network.NetworkInterceptor` to capture and assert on the
requests a page fires — see [JSON-RPC / network interception](../README.md#json-rpc--network-interception)
and Example B in [examples/README.md](../examples/README.md).

**8. Run a UI + API + Database validation**

This is the framework's key differentiator: one call dispatches whichever
layers you need.

```python
from framework.hybrid import ValidationFacade, ValidationMode

facade = ValidationFacade(ValidationMode.UI_API_DATABASE)
result = facade.run(ui_value=..., api_value=..., db_value=..., tolerance=...)
```

See Example F — the full, runnable, copy-pasteable version — in
[examples/data_validation/test_ui_api_database_validation_example.py](../examples/data_validation/test_ui_api_database_validation_example.py)
and [examples/README.md](../examples/README.md).

**9. Analyze an existing automation framework**

Point the sync CLI at any local directory, `.zip`, or git URL (including
`file://`) of a framework you're considering migrating from:

```bash
poetry run python -m framework.sync analyze /path/to/old-framework --report analysis.json
```

**10. Generate a migration worksheet**

```bash
poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/
```

This writes `generated/MIGRATION_WORKSHEET.md` — a review document, never
generated source code. See [docs/FrameworkSync.md](FrameworkSync.md) for
what `analyze`/`scaffold` do and don't do.

**11. Extend an existing framework for a new UI**

If the customer is adding a new UI on an existing backend, keep the existing
automation ecosystem and produce a reviewable reuse plan instead of a second
framework:

```bash
poetry run python -m framework sync analyze /path/to/existing-framework --report existing.json
poetry run python -m framework discover ui https://new-ui.example.test --capture-network --report new-ui.json
poetry run python -m framework extension analyze \
  --discovery-report new-ui.json \
  --sync-report existing.json \
  --output extension-plan.json
```

`--capture-network` is deliberately opt-in. The discovery report persists
only request/response shape (method, path, status, and key names), never
headers, body values, tokens, or credentials. The extension report identifies
evidence-backed reuse candidates and classifies each as reuse, extend, create,
unknown, or manual review; it never alters either application.

## Troubleshooting

See [Troubleshooting.md](Troubleshooting.md).
