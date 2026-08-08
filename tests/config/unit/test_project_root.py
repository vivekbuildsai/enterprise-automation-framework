from __future__ import annotations

from pathlib import Path

import pytest

from framework import project_root as project_root_module

pytestmark = pytest.mark.config


def test_explicit_env_var_wins_over_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "explicit-root"
    explicit.mkdir()
    cwd_with_marker = tmp_path / "cwd-with-marker"
    (cwd_with_marker / "config" / "environments").mkdir(parents=True)

    monkeypatch.setenv("AUTOMATION_PROJECT_ROOT", str(explicit))
    monkeypatch.chdir(cwd_with_marker)

    assert project_root_module.resolve_project_root() == explicit


def test_explicit_env_var_expands_user_and_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real-root"
    real.mkdir()
    relative_alias = tmp_path / "alias" / ".." / "real-root"

    monkeypatch.setenv("AUTOMATION_PROJECT_ROOT", str(relative_alias))

    assert project_root_module.resolve_project_root() == real


def test_cwd_with_project_marker_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "config" / "environments").mkdir(parents=True)
    monkeypatch.delenv("AUTOMATION_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    assert project_root_module.resolve_project_root() == tmp_path


def test_falls_back_to_package_location_when_no_marker_and_no_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates a customer project whose cwd has no `config/environments/`
    yet (e.g. a one-off script) — must fall back to the *package's own*
    location rather than raising, matching pre-hardening behavior for this
    one case.
    """
    monkeypatch.delenv("AUTOMATION_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    expected_fallback = Path(project_root_module.__file__).resolve().parents[1]
    assert project_root_module.resolve_project_root() == expected_fallback


def test_module_level_project_root_matches_repo_root_in_dev() -> None:
    """`PROJECT_ROOT` is computed once at import time — sanity-check it
    landed on this repo's own root (not inside site-packages) when running
    the framework's own test suite from the repo root, exactly as every
    consumer module (`config.settings`, `logger`, `driver_manager`, ...)
    expects.
    """
    assert (project_root_module.PROJECT_ROOT / "config" / "environments").is_dir()
    assert (project_root_module.PROJECT_ROOT / "framework").is_dir()
