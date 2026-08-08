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

## Troubleshooting

See [Troubleshooting.md](Troubleshooting.md).
