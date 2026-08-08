from __future__ import annotations

import time
from pathlib import Path

from framework.exceptions import AutomationFrameworkError


class FileUtils:
    """Filesystem helpers for verifying downloads and reading test-generated
    files — deliberately thin wrappers over `pathlib`, not a new abstraction,
    since the value here is the *wait-for-download* semantics, not hiding
    `Path`.
    """

    @staticmethod
    def wait_for_file(
        path: str | Path, *, timeout_seconds: float = 10, poll_seconds: float = 0.2
    ) -> Path:
        """Polls until `path` exists (a download in progress may not be on
        disk the instant the triggering click returns) — prefer
        `BasePage.download_file()`/`expect_download()` when possible, since
        those key off Playwright's own download-complete event rather than
        polling the filesystem; this exists for the cases where a download
        is triggered indirectly and there's no click to wrap.
        """
        target = Path(path)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if target.exists():
                return target
            time.sleep(poll_seconds)
        raise AutomationFrameworkError(
            f"File never appeared at '{target}' within {timeout_seconds}s"
        )

    @staticmethod
    def read_text(path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def file_size_bytes(path: str | Path) -> int:
        return Path(path).stat().st_size

    @staticmethod
    def delete_if_exists(path: str | Path) -> None:
        Path(path).unlink(missing_ok=True)
