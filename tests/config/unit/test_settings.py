from __future__ import annotations

import os
from pathlib import Path

import pytest

from framework.config import get_settings
from framework.config import settings as settings_module
from framework.enums.environment import Environment

pytestmark = pytest.mark.config

_DEV_YAML = """
validation_mode: ui_only
ui:
  base_url: "${AUTOMATION_UI_BASE_URL:-https://example.invalid}"
  login_username: "${AUTOMATION_UI_USERNAME:-default_user}"
  login_password: "${AUTOMATION_UI_PASSWORD:-default_pass}"
browser:
  action_timeout_ms: "${AUTOMATION_ACTION_TIMEOUT_MS:-15000}"
  headless: "${AUTOMATION_HEADLESS:-true}"
"""


@pytest.fixture(autouse=True)
def _isolated_environ() -> None:
    """`load_dotenv` mutates the real `os.environ` directly (not through
    `monkeypatch`), so a snapshot/restore is required on top of `monkeypatch`
    to stop one test's fake `.env`/`.env.dev` values leaking into the next.

    Stripping every `AUTOMATION_*` key up front matters just as much as restoring
    afterwards: earlier tests in the *same* pytest session (e.g. any test
    using the real `settings` fixture) may already have called
    `load_dotenv(real_repo/.env, override=False)`, which sets e.g.
    `AUTOMATION_UI_USERNAME` process-wide. Without clearing it here first, this
    module's own `load_dotenv(tmp_path/.env, override=False)` calls would
    see that key as "already set" and silently skip loading the fake value.
    """
    original = dict(os.environ)
    for key in list(os.environ):
        if key.startswith("AUTOMATION_"):
            del os.environ[key]
    settings_module.get_settings.cache_clear()
    yield
    os.environ.clear()
    os.environ.update(original)
    settings_module.get_settings.cache_clear()


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the settings module at an isolated fake project root — a real
    dev.yaml plus whatever `.env`/`.env.dev` files each test writes — so
    these tests exercise the actual dotenv-layering code path without
    touching this repo's real `.env`/config files.
    """
    monkeypatch.setattr(settings_module, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(settings_module, "_CONFIG_DIR", tmp_path / "config" / "environments")
    config_dir = tmp_path / "config" / "environments"
    config_dir.mkdir(parents=True)
    (config_dir / "dev.yaml").write_text(_DEV_YAML, encoding="utf-8")
    return tmp_path


def test_env_specific_file_overrides_shared_env_file(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / ".env").write_text("AUTOMATION_ACTION_TIMEOUT_MS=1000\n", encoding="utf-8")
    (project_root / ".env.dev").write_text("AUTOMATION_ACTION_TIMEOUT_MS=2000\n", encoding="utf-8")
    monkeypatch.setenv("AUTOMATION_ENV", "dev")

    assert get_settings().browser.action_timeout_ms == 2000


def test_shared_file_fills_gaps_not_set_by_env_specific_file(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / ".env").write_text("AUTOMATION_UI_USERNAME=shared_user\n", encoding="utf-8")
    (project_root / ".env.dev").write_text("AUTOMATION_ACTION_TIMEOUT_MS=2000\n", encoding="utf-8")
    monkeypatch.setenv("AUTOMATION_ENV", "dev")

    settings = get_settings()

    assert settings.ui.login_username == "shared_user"
    assert settings.browser.action_timeout_ms == 2000


def test_real_process_env_var_wins_over_both_files(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / ".env").write_text("AUTOMATION_ACTION_TIMEOUT_MS=1000\n", encoding="utf-8")
    (project_root / ".env.dev").write_text("AUTOMATION_ACTION_TIMEOUT_MS=2000\n", encoding="utf-8")
    monkeypatch.setenv("AUTOMATION_ENV", "dev")
    monkeypatch.setenv("AUTOMATION_ACTION_TIMEOUT_MS", "3000")

    assert get_settings().browser.action_timeout_ms == 3000


def test_missing_env_specific_file_is_not_an_error(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / ".env").write_text("AUTOMATION_ACTION_TIMEOUT_MS=1000\n", encoding="utf-8")
    monkeypatch.setenv("AUTOMATION_ENV", "dev")

    assert get_settings().browser.action_timeout_ms == 1000


def test_yaml_default_used_when_nothing_overrides_it(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTOMATION_ENV", "dev")

    settings = get_settings()

    assert settings.browser.action_timeout_ms == 15000
    assert settings.browser.headless is True


def test_environment_resolved_from_shared_env_file_automation_env(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AUTOMATION_ENV", raising=False)
    (project_root / ".env").write_text("AUTOMATION_ENV=dev\n", encoding="utf-8")

    assert get_settings().environment == Environment.DEV


def test_real_process_automation_env_wins_over_shared_env_file(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project_root / ".env").write_text("AUTOMATION_ENV=qa\n", encoding="utf-8")
    (project_root / "config" / "environments" / "qa.yaml").write_text(_DEV_YAML, encoding="utf-8")
    monkeypatch.setenv("AUTOMATION_ENV", "dev")

    assert get_settings().environment == Environment.DEV
