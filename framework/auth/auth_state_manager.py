from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext

from framework.exceptions import AuthenticationError
from framework.logger import get_logger
from framework.project_root import PROJECT_ROOT

_logger = get_logger("AuthStateManager")


class AuthStateManager:
    """Saves, validates, and reuses a Playwright ``storage_state`` snapshot
    (cookies + localStorage) so tests can start already authenticated instead
    of driving a real login form every time — the ``.auth/*.json`` +
    global-setup pattern common in enterprise Playwright/TypeScript
    frameworks, reimplemented here for the sync Python API.

    A saved state is considered stale (and is regenerated on next use) once
    it is older than ``max_age_seconds``, or once every cookie it contains
    has an ``expires`` timestamp in the past — whichever comes first. Session
    cookies (``expires == -1``) never expire this way and rely solely on the
    age check.
    """

    def __init__(self, state_dir: str = ".auth", max_age_seconds: int = 28_800) -> None:
        self._dir = PROJECT_ROOT / state_dir
        self._max_age_seconds = max_age_seconds

    def path_for(self, profile: str) -> Path:
        return self._dir / f"{profile}.json"

    def is_valid(self, profile: str) -> bool:
        """True if a saved state exists for `profile` and neither the file
        age nor its cookies' `expires` timestamps indicate it has expired.
        """
        state_path = self.path_for(profile)
        if not state_path.exists():
            return False

        age_seconds = time.time() - state_path.stat().st_mtime
        if age_seconds > self._max_age_seconds:
            _logger.info(f"Auth state '{profile}' expired by age ({age_seconds:.0f}s)")
            return False

        try:
            raw: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning(f"Auth state '{profile}' unreadable, treating as invalid: {exc}")
            return False

        cookies = raw.get("cookies", [])
        expiring_cookies = [c for c in cookies if c.get("expires", -1) not in (-1, None)]
        if expiring_cookies and all(c["expires"] < time.time() for c in expiring_cookies):
            _logger.info(f"Auth state '{profile}' expired (all cookies past expiry)")
            return False

        return True

    def save(self, context: BrowserContext, profile: str) -> Path:
        state_path = self.path_for(profile)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(state_path))
        _logger.info(f"Saved auth state '{profile}' to {state_path}")
        return state_path

    def clear(self, profile: str) -> None:
        self.path_for(profile).unlink(missing_ok=True)

    def load_or_create(
        self,
        *,
        profile: str,
        browser: Browser,
        login: Callable[[BrowserContext], None],
        context_kwargs: dict[str, Any] | None = None,
    ) -> Path:
        """Ensure a fresh state file exists for `profile`, regenerating it via
        `login` (given a brand-new, unauthenticated `BrowserContext`) when
        missing or expired. Returns the state path — pass it as
        `storage_state=` to `browser.new_context()` / `DriverManager` in
        actual test sessions to start pre-authenticated.
        """
        if self.is_valid(profile):
            return self.path_for(profile)

        _logger.info(f"Regenerating auth state '{profile}'")
        context = browser.new_context(**(context_kwargs or {}))
        try:
            login(context)
        except Exception as exc:
            context.close()
            raise AuthenticationError(
                f"Failed to establish authenticated session for profile '{profile}': {exc}"
            ) from exc

        state_path = self.save(context, profile)
        context.close()
        return state_path
