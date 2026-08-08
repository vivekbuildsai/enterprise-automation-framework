from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argv, no shell, used for `git clone` only
import tempfile
import zipfile
from pathlib import Path
from typing import Protocol

from framework.exceptions import ConfigurationError
from framework.logger import get_logger

_logger = get_logger("RepositorySource")


class RepositorySource(Protocol):
    """Produces a local directory for `RepositoryAnalyzer` to read —
    read-only from the analyzer's perspective either way. `cleanup()`
    removes anything this source created (a temp extraction/clone dir);
    it's always safe to call even if `materialize()` was never called or
    failed partway through.
    """

    def materialize(self) -> Path: ...

    def cleanup(self) -> None: ...


class LocalDirectorySource:
    """Analyzes a directory the caller already has on disk — never
    copies or modifies it.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.is_dir():
            raise ConfigurationError(f"Not a directory: {self._path}")

    def materialize(self) -> Path:
        return self._path

    def cleanup(self) -> None:
        pass


class ZipArchiveSource:
    """Secure extraction into a fresh temp directory: rejects any archive
    member whose resolved path would land outside the extraction
    directory (zip-slip protection). Never executes anything from the
    archive — this only extracts files for read-only static analysis.
    """

    def __init__(self, zip_path: str | Path) -> None:
        self._zip_path = Path(zip_path)
        self._extract_dir: Path | None = None

    def materialize(self) -> Path:
        extract_dir = Path(tempfile.mkdtemp(prefix="framework_sync_zip_"))
        self._extract_dir = extract_dir
        resolved_root = extract_dir.resolve()

        with zipfile.ZipFile(self._zip_path) as archive:
            for member in archive.infolist():
                target = self._safe_target(resolved_root, member.filename)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, open(target, "wb") as dest:
                    shutil.copyfileobj(source, dest)

        return extract_dir

    @staticmethod
    def _safe_target(resolved_root: Path, member_name: str) -> Path:
        target = (resolved_root / member_name).resolve()
        if target != resolved_root and resolved_root not in target.parents:
            raise ConfigurationError(f"Unsafe archive member (path traversal): {member_name!r}")
        return target

    def cleanup(self) -> None:
        if self._extract_dir and self._extract_dir.exists():
            shutil.rmtree(self._extract_dir, ignore_errors=True)


class GitRepositorySource:
    """Clones a git URL (GitHub/GitLab/Bitbucket/self-hosted, or a local
    `file://`/path) via a plain `git clone --depth 1` subprocess — this
    covers "a GitHub repository URL" without needing GitHub's API or a
    token for public repositories. Private repositories rely entirely on
    the caller's own already-configured git credentials (SSH agent /
    credential manager, set up outside this framework) — this class never
    prompts for, stores, or logs a credential; if the clone fails, the
    reason git itself reports is surfaced as-is (never a
    fabricated/guessed cause).
    """

    def __init__(self, url: str, *, timeout_seconds: float = 300) -> None:
        self._url = url
        self._timeout = timeout_seconds
        self._clone_dir: Path | None = None

    def materialize(self) -> Path:
        clone_dir = Path(tempfile.mkdtemp(prefix="framework_sync_git_"))
        self._clone_dir = clone_dir
        result = subprocess.run(  # nosec - fixed argv, shell=False, `git` resolved via PATH intentionally
            ["git", "clone", "--depth", "1", self._url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=False,
        )
        if result.returncode != 0:
            self.cleanup()
            raise ConfigurationError(
                f"git clone failed for {self._url!r}: {result.stderr.strip()[:500]}"
            )
        return clone_dir

    def cleanup(self) -> None:
        if self._clone_dir and self._clone_dir.exists():
            shutil.rmtree(self._clone_dir, ignore_errors=True)
