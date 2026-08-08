from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import Locator, Page

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCREENSHOTS_DIR = _PROJECT_ROOT / "artifacts" / "screenshots"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


class ScreenshotUtils:
    """Named, organized screenshot capture — distinct from
    `BasePage.screenshot()`/`element_screenshot()` (which just wrap the raw
    Playwright call for a caller who already has a path in mind). This class
    owns *where* on-demand captures land: `artifacts/screenshots/<name>_<timestamp>.png`,
    so ad-hoc "success" screenshots during a run don't collide with or
    overwrite each other or the failure screenshots `DriverManager` saves.
    """

    @staticmethod
    def capture_full_page(page: Page, name: str) -> Path:
        _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path = _SCREENSHOTS_DIR / f"{_safe_name(name)}_{timestamp}.png"
        page.screenshot(path=str(path), full_page=True)
        return path

    @staticmethod
    def capture_element(locator: Locator, name: str) -> Path:
        _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path = _SCREENSHOTS_DIR / f"{_safe_name(name)}_{timestamp}.png"
        locator.screenshot(path=str(path))
        return path
