from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from framework.auth import AuthStateManager
from framework.exceptions import AuthenticationError

pytestmark = pytest.mark.auth


class FakeContext:
    """Duck-typed stand-in for `playwright.sync_api.BrowserContext` — only
    implements the surface `AuthStateManager` actually touches.
    """

    def __init__(self, state: dict[str, Any] | None = None, *, fail_login: bool = False) -> None:
        self._state = state or {"cookies": [], "origins": []}
        self.fail_login = fail_login
        self.closed = False

    def storage_state(self, path: str) -> None:
        Path(path).write_text(json.dumps(self._state), encoding="utf-8")

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext) -> None:
        self._context = context
        self.new_context_kwargs: dict[str, Any] | None = None

    def new_context(self, **kwargs: Any) -> FakeContext:
        self.new_context_kwargs = kwargs
        return self._context


def _write_state(path: Path, cookies: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cookies": cookies, "origins": []}), encoding="utf-8")


@pytest.fixture
def manager(tmp_path: Path) -> AuthStateManager:
    return AuthStateManager(state_dir=str(tmp_path / ".auth"), max_age_seconds=3600)


class TestIsValid:
    def test_false_when_file_missing(self, manager: AuthStateManager) -> None:
        assert manager.is_valid("user") is False

    def test_true_for_fresh_state_with_session_cookies(self, manager: AuthStateManager) -> None:
        _write_state(manager.path_for("user"), cookies=[{"name": "session", "expires": -1}])
        assert manager.is_valid("user") is True

    def test_false_when_file_older_than_max_age(self, manager: AuthStateManager) -> None:
        state_path = manager.path_for("user")
        _write_state(state_path, cookies=[{"name": "session", "expires": -1}])
        stale_time = time.time() - 7200
        os.utime(state_path, (stale_time, stale_time))

        assert manager.is_valid("user") is False

    def test_false_when_all_cookies_expired(self, manager: AuthStateManager) -> None:
        _write_state(
            manager.path_for("user"), cookies=[{"name": "session", "expires": time.time() - 60}]
        )
        assert manager.is_valid("user") is False

    def test_true_when_any_cookie_still_unexpired(self, manager: AuthStateManager) -> None:
        _write_state(
            manager.path_for("user"),
            cookies=[
                {"name": "expired", "expires": time.time() - 60},
                {"name": "live", "expires": time.time() + 3600},
            ],
        )
        assert manager.is_valid("user") is True

    def test_false_for_unreadable_json(self, manager: AuthStateManager) -> None:
        state_path = manager.path_for("user")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("not json", encoding="utf-8")
        assert manager.is_valid("user") is False


class TestSaveAndClear:
    def test_save_writes_state_file(self, manager: AuthStateManager) -> None:
        context = FakeContext({"cookies": [{"name": "session", "expires": -1}], "origins": []})
        saved_path = manager.save(context, "user")

        assert saved_path == manager.path_for("user")
        assert saved_path.exists()
        assert json.loads(saved_path.read_text())["cookies"][0]["name"] == "session"

    def test_clear_removes_existing_file_without_error(self, manager: AuthStateManager) -> None:
        _write_state(manager.path_for("user"), cookies=[])
        manager.clear("user")
        assert not manager.path_for("user").exists()

    def test_clear_is_a_noop_when_file_absent(self, manager: AuthStateManager) -> None:
        manager.clear("does-not-exist")  # must not raise


class TestLoadOrCreate:
    def test_returns_existing_path_without_logging_in_when_valid(
        self, manager: AuthStateManager
    ) -> None:
        _write_state(manager.path_for("user"), cookies=[{"name": "session", "expires": -1}])
        login_calls: list[FakeContext] = []

        result = manager.load_or_create(
            profile="user",
            browser=FakeBrowser(FakeContext()),  # type: ignore[arg-type]
            login=login_calls.append,
        )

        assert result == manager.path_for("user")
        assert login_calls == []

    def test_regenerates_via_login_when_missing(self, manager: AuthStateManager) -> None:
        context = FakeContext({"cookies": [{"name": "session", "expires": -1}], "origins": []})
        browser = FakeBrowser(context)
        login_calls: list[FakeContext] = []

        result = manager.load_or_create(
            profile="user", browser=browser, login=login_calls.append  # type: ignore[arg-type]
        )

        assert login_calls == [context]
        assert result.exists()
        assert context.closed is True

    def test_wraps_login_failure_in_authentication_error(self, manager: AuthStateManager) -> None:
        context = FakeContext()
        browser = FakeBrowser(context)

        def _failing_login(_: FakeContext) -> None:
            raise RuntimeError("could not reach login page")

        with pytest.raises(AuthenticationError, match="user"):
            manager.load_or_create(
                profile="user", browser=browser, login=_failing_login  # type: ignore[arg-type]
            )
        assert context.closed is True
        assert not manager.path_for("user").exists()
