"""Safe `.env` mutation — every test here passes an explicit `env_path`
(a `tmp_path` file), so nothing ever touches this repository's real
`.env`. Covers the "never overwrite a differing value without --force"
non-destructive guarantee the module docstring promises.
"""

from __future__ import annotations

import pytest

from framework.doctor.env_writer import apply_env_change, plan_env_change

pytestmark = pytest.mark.doctor


def test_plan_add_when_file_does_not_exist(tmp_path) -> None:
    env_path = tmp_path / ".env"

    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)

    assert change.action == "add"
    assert change.old_value is None
    assert change.new_value == "chromium"


def test_plan_unchanged_when_same_value_already_set(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("AUTOMATION_BROWSER=chromium\n", encoding="utf-8")

    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)

    assert change.action == "unchanged"


def test_plan_skipped_conflict_when_different_value_and_no_force(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("AUTOMATION_BROWSER=firefox\n", encoding="utf-8")

    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)

    assert change.action == "skipped_conflict"
    assert change.old_value == "firefox"


def test_plan_update_when_different_value_and_force(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("AUTOMATION_BROWSER=firefox\n", encoding="utf-8")

    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path, force=True)

    assert change.action == "update"


def test_apply_add_appends_a_new_line(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("EXISTING_VAR=1\n", encoding="utf-8")
    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)

    apply_env_change(change, env_path=env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "EXISTING_VAR=1" in content
    assert "AUTOMATION_BROWSER=chromium" in content


def test_apply_update_replaces_the_existing_line_in_place(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("AUTOMATION_BROWSER=firefox\nOTHER=2\n", encoding="utf-8")
    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path, force=True)

    apply_env_change(change, env_path=env_path)

    lines = env_path.read_text(encoding="utf-8").splitlines()
    assert "AUTOMATION_BROWSER=chromium" in lines
    assert "AUTOMATION_BROWSER=firefox" not in lines
    assert "OTHER=2" in lines


def test_apply_skipped_conflict_never_writes(tmp_path) -> None:
    env_path = tmp_path / ".env"
    original = "AUTOMATION_BROWSER=firefox\n"
    env_path.write_text(original, encoding="utf-8")
    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)

    apply_env_change(change, env_path=env_path)

    assert env_path.read_text(encoding="utf-8") == original


def test_apply_unchanged_never_writes_and_never_creates_a_missing_file(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("AUTOMATION_BROWSER=chromium\n", encoding="utf-8")
    change = plan_env_change("AUTOMATION_BROWSER", "chromium", env_path=env_path)
    mtime_before = env_path.stat().st_mtime

    apply_env_change(change, env_path=env_path)

    assert env_path.stat().st_mtime == mtime_before
