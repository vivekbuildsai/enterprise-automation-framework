from __future__ import annotations

import contextlib
import re
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from framework.config.models import BrowserConfig
from framework.drivers.browser_factory import BrowserFactory
from framework.logger import get_logger
from framework.project_root import PROJECT_ROOT

_logger = get_logger("DriverManager")
_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


class DriverManager:
    """Owns the Playwright lifecycle for a single test: opens an isolated
    context/page on a `Browser` (its own, or a shared one handed in by the
    caller) and captures trace/video/screenshot/HAR artifacts only when the
    test actually failed — keeping green runs cheap while still supporting
    Trace Viewer debugging on failures.

    One instance per test (see `framework/fixtures/driver_fixtures.py`).
    `pytest-xdist -n auto` parallel-safety comes from each *worker* owning
    its own browser process (a `session`-scoped fixture is per-worker, not
    global) — it was never about needing a fresh browser *per test*, only a
    fresh, isolated `BrowserContext` per test, which Playwright already
    guarantees (separate cookies/storage/cache) whether or not the
    underlying browser process is shared. Pass `browser=` to reuse an
    already-running one (the common case via the `page`/`authenticated_page`
    fixtures); omit it to launch and own a dedicated browser+Playwright for
    this instance's lifetime (standalone/backward-compatible usage) —
    `finalize()` only closes what this instance itself launched.
    """

    def __init__(
        self,
        config: BrowserConfig,
        test_name: str,
        storage_state: Path | None = None,
        browser: Browser | None = None,
    ) -> None:
        self._config = config
        self._test_name = _safe_name(test_name)
        self._storage_state = storage_state
        self._playwright: Playwright | None = None
        self._browser: Browser | None = browser
        self._owns_browser = browser is None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def start(self) -> Page:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = BrowserFactory.launch(self._playwright, self._config)

        context_kwargs: dict[str, object] = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
        }
        if self._storage_state is not None:
            context_kwargs["storage_state"] = str(self._storage_state)
        if self._config.video_on_failure:
            context_kwargs["record_video_dir"] = str(_ARTIFACTS_DIR / "videos")
        if self._config.har_recording:
            context_kwargs["record_har_path"] = str(
                _ARTIFACTS_DIR / "har" / f"{self._test_name}.har"
            )

        self._context = self._browser.new_context(**context_kwargs)  # type: ignore[arg-type]
        self._context.set_default_timeout(self._config.action_timeout_ms)
        self._context.set_default_navigation_timeout(self._config.navigation_timeout_ms)

        if self._config.trace_on_failure:
            self._context.tracing.start(screenshots=True, snapshots=True, sources=True)

        self._page = self._context.new_page()
        _logger.info(f"Driver session started for test '{self._test_name}'")
        return self._page

    def finalize(self, *, test_failed: bool) -> None:
        if self._context is None or self._page is None:
            return

        if test_failed:
            self._capture_failure_artifacts()
        elif self._config.trace_on_failure:
            self._context.tracing.stop()

        video = self._page.video
        self._page.close()
        self._context.close()

        if video and not test_failed and self._config.video_on_failure:
            # Only failures are worth keeping; discard video for passing tests.
            with contextlib.suppress(Exception):
                Path(video.path()).unlink(missing_ok=True)

        # A shared/injected browser outlives this test — only close what this
        # instance itself launched (standalone usage with no `browser=` arg).
        if self._owns_browser:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()

        _logger.info(
            f"Driver session finalized for test '{self._test_name}' (failed={test_failed})"
        )

    def _capture_failure_artifacts(self) -> None:
        assert (
            self._context is not None and self._page is not None
        )  # nosec B101 - internal invariant, not user input

        if self._config.screenshot_on_failure:
            screenshot_path = _ARTIFACTS_DIR / "screenshots" / f"{self._test_name}.png"
            self._page.screenshot(path=str(screenshot_path), full_page=True)
            _logger.warning(f"Saved failure screenshot: {screenshot_path}")

        if self._config.trace_on_failure:
            trace_path = _ARTIFACTS_DIR / "traces" / f"{self._test_name}.zip"
            self._context.tracing.stop(path=str(trace_path))
            _logger.warning(f"Saved failure trace: {trace_path}")
