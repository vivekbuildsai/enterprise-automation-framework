"""Environment capability detectors — stdlib-only (plus the already-a-
dependency `playwright` package for its own managed-browser paths), no
new third-party dependency. Every detector is a pure "look and report"
function: none of them install, launch, or modify anything. A detector
never raises — an absent/broken tool becomes a `MISSING`/`DEGRADED`
capability, not an exception, since "this optional tool isn't here" is
the normal, expected case doctor exists to describe.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess  # nosec B404 - fixed argv, no shell, version/detection probes only
import sys
from pathlib import Path

from framework.doctor.models import CapabilityCategory, CapabilityStatus, EnvironmentCapability
from framework.project_root import PROJECT_ROOT

_PROBE_TIMEOUT_SECONDS = 5


def _run(
    cmd: list[str], *, timeout: float = _PROBE_TIMEOUT_SECONDS, cwd: Path | None = None
) -> str | None:
    """Runs a fixed-argv, shell-free probe command and returns its first
    stdout line — or `None` for any failure (not found, non-zero exit,
    timeout). Never raises; a failed probe is exactly as informative as a
    successful one here (it means "not available"). `cwd` defaults to the
    process's actual working directory (`subprocess.run`'s own default) —
    only git detection overrides it to `PROJECT_ROOT` explicitly, since
    "which repository" must never depend on ambient process cwd (the same
    project-root discipline every other project-path-sensitive module in
    this framework already follows).
    """
    try:
        result = subprocess.run(  # nosec B603 - fixed argv, shell=False, version probes only
            cmd, capture_output=True, text=True, timeout=timeout, check=False, cwd=cwd
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    output = (result.stdout or result.stderr or "").strip().splitlines()
    return output[0].strip() if output else None


def _available(
    *,
    name: str,
    category: CapabilityCategory,
    found: bool,
    version: str | None = None,
    path: str | None = None,
    required: bool = False,
    reason: str = "",
    remediation: str = "",
) -> EnvironmentCapability:
    """`reason`/`remediation` only ever surface when the capability is
    genuinely absent — an `AVAILABLE` capability never shows install
    instructions for itself. `MISSING` (not `NOT_REQUIRED`) is the default
    for an absent optional tool at the detector layer: whether an absent
    tool is truly "not needed" is a judgment only the browser-recommendation
    step (which knows what was actually selected) can make — see
    `framework.doctor.report.apply_not_required_downgrades`.
    """
    status = CapabilityStatus.AVAILABLE if found else CapabilityStatus.MISSING
    return EnvironmentCapability(
        name=name,
        category=category,
        available=found,
        version=version,
        path=path,
        required=required,
        status=status,
        reason="" if found else reason,
        remediation="" if found else remediation,
    )


# --- Operating system --------------------------------------------------------


def detect_operating_system() -> list[EnvironmentCapability]:
    system = platform.system()  # "Windows" | "Linux" | "Darwin"
    label = {"Darwin": "macOS"}.get(system, system)
    return [
        EnvironmentCapability(
            name="Operating System",
            category=CapabilityCategory.OPERATING_SYSTEM,
            available=True,
            version=f"{label} {platform.release()}",
            path=None,
            required=True,
            status=CapabilityStatus.AVAILABLE,
            reason=f"Detected via platform.system() = {system!r}",
        ),
        EnvironmentCapability(
            name="Architecture",
            category=CapabilityCategory.OPERATING_SYSTEM,
            available=True,
            version=platform.machine(),
            required=False,
            status=CapabilityStatus.AVAILABLE,
        ),
    ]


# --- Python -------------------------------------------------------------


def _venv_active() -> bool:
    return sys.prefix != sys.base_prefix or bool(os.environ.get("VIRTUAL_ENV"))


def detect_python() -> list[EnvironmentCapability]:
    capabilities = [
        EnvironmentCapability(
            name="Python",
            category=CapabilityCategory.PYTHON,
            available=True,
            version=platform.python_version(),
            path=sys.executable,
            required=True,
            status=CapabilityStatus.AVAILABLE,
        ),
        EnvironmentCapability(
            name="Virtual Environment",
            category=CapabilityCategory.PYTHON,
            available=_venv_active(),
            required=False,
            status=(
                CapabilityStatus.AVAILABLE if _venv_active() else CapabilityStatus.NOT_REQUIRED
            ),
            reason="" if _venv_active() else "Running against the system/base Python interpreter.",
        ),
    ]

    poetry_path = shutil.which("poetry")
    poetry_version = _run([poetry_path, "--version"]) if poetry_path else None
    capabilities.append(
        _available(
            name="Poetry",
            category=CapabilityCategory.PYTHON,
            found=poetry_path is not None,
            version=poetry_version,
            path=poetry_path,
            required=False,
            remediation="Install from https://python-poetry.org/docs/#installation",
        )
    )
    return capabilities


# --- Node ecosystem -------------------------------------------------------


def detect_node() -> list[EnvironmentCapability]:
    capabilities = []
    for tool, remediation in (
        ("node", "Install Node.js from https://nodejs.org/ (LTS release recommended)."),
        ("npm", "npm ships with Node.js — reinstall Node.js from https://nodejs.org/."),
        ("npx", "npx ships with npm 5.2+ — update npm: npm install -g npm@latest"),
    ):
        path = shutil.which(tool)
        version = _run([path, "--version"]) if path else None
        capabilities.append(
            _available(
                name=tool,
                category=CapabilityCategory.NODE,
                found=path is not None,
                version=version,
                path=path,
                required=False,
                remediation=remediation,
            )
        )
    return capabilities


# --- Browsers ---------------------------------------------------------------

_EDGE_CANDIDATES: dict[str, list[str]] = {
    "Windows": [
        r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
        r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
    ],
    "Darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
    "Linux": ["microsoft-edge", "microsoft-edge-stable", "microsoft-edge-beta"],
}
_CHROME_CANDIDATES: dict[str, list[str]] = {
    "Windows": [
        r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
        r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ],
    "Darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
    "Linux": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
}
_FIREFOX_CANDIDATES: dict[str, list[str]] = {
    "Windows": [
        r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe",
        r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe",
    ],
    "Darwin": ["/Applications/Firefox.app/Contents/MacOS/firefox"],
    "Linux": ["firefox"],
}


def _find_executable(candidates: list[str]) -> str | None:
    """Each candidate is either an absolute/`%VAR%`-templated path (checked
    for real existence on disk) or a bare command name (resolved via
    `shutil.which` on `PATH`) — covers both "installed to its conventional
    location" (Windows/macOS) and "installed as a PATH-visible command"
    (Linux package managers) without guessing which applies.
    """
    for candidate in candidates:
        if "%" in candidate or candidate.startswith(("/", "\\")):
            expanded = os.path.expandvars(candidate)
            if "%" not in expanded and Path(expanded).exists():
                return expanded
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _system_browser_capability(
    name: str, candidates_by_os: dict[str, list[str]], version_flag: str = "--version"
) -> EnvironmentCapability:
    system = platform.system()
    candidates = candidates_by_os.get(system, [])
    path = _find_executable(candidates)
    version = _run([path, version_flag]) if path else None
    return _available(
        name=name,
        category=CapabilityCategory.BROWSER,
        found=path is not None,
        version=version,
        path=path,
        required=False,
        remediation=f"{name} was not found on this machine — install it, or use a different "
        "browser this doctor detected as AVAILABLE.",
    )


def _playwright_managed_browser_capability(engine_name: str, label: str) -> EnvironmentCapability:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _available(
            name=label,
            category=CapabilityCategory.BROWSER,
            found=False,
            required=False,
            reason="The `playwright` package is not importable.",
            remediation="poetry install",
        )

    try:
        with sync_playwright() as playwright:
            engine = getattr(playwright, engine_name)
            executable_path = engine.executable_path
            found = bool(executable_path) and Path(executable_path).exists()
            return _available(
                name=label,
                category=CapabilityCategory.BROWSER,
                found=found,
                path=executable_path if found else None,
                required=False,
                remediation=f"poetry run playwright install {engine_name}",
            )
    except Exception as exc:  # noqa: BLE001 - a probe failure is a MISSING result, not a crash
        return _available(
            name=label,
            category=CapabilityCategory.BROWSER,
            found=False,
            required=False,
            reason=f"Could not query Playwright's browser cache: {exc}",
            remediation=f"poetry run playwright install {engine_name}",
        )


def detect_browsers() -> list[EnvironmentCapability]:
    """Deliberately never assumes the bundled Playwright Chromium build is
    the answer — reports Edge/Chrome/Firefox (real, system-installed
    executables) and Playwright's own managed Chromium/Firefox/WebKit
    builds as five independent, equally-inspectable facts. Selecting
    *which one* to use is `recommend_browser`'s job, not this function's.
    """
    return [
        _system_browser_capability("Microsoft Edge", _EDGE_CANDIDATES),
        _system_browser_capability("Google Chrome", _CHROME_CANDIDATES),
        _system_browser_capability("Firefox", _FIREFOX_CANDIDATES),
        _playwright_managed_browser_capability("chromium", "Playwright Chromium"),
        _playwright_managed_browser_capability("firefox", "Playwright Firefox"),
        _playwright_managed_browser_capability("webkit", "Playwright WebKit"),
    ]


# --- FFmpeg -------------------------------------------------------------


def detect_ffmpeg(*, required: bool = False) -> EnvironmentCapability:
    path = shutil.which("ffmpeg")
    version_line = _run([path, "-version"]) if path else None
    # `ffmpeg -version`'s first line looks like "ffmpeg version 6.0 ..." —
    # trimmed down to just the version token for a concise report.
    version = None
    if version_line and version_line.lower().startswith("ffmpeg version"):
        parts = version_line.split()
        version = parts[2] if len(parts) > 2 else version_line
    return _available(
        name="FFmpeg",
        category=CapabilityCategory.FFMPEG,
        found=path is not None,
        version=version,
        path=path,
        required=required,
        reason="Only required for video-artifact workflows that need post-processing.",
        remediation="Install from https://ffmpeg.org/download.html "
        "(or `brew install ffmpeg` / `choco install ffmpeg` / `apt install ffmpeg`).",
    )


# --- Docker -------------------------------------------------------------


def detect_docker() -> list[EnvironmentCapability]:
    docker_path = shutil.which("docker")
    docker_version = _run([docker_path, "--version"]) if docker_path else None
    daemon_running = False
    if docker_path:
        # `docker info` only succeeds if the daemon is actually reachable —
        # distinguishes "docker CLI installed" from "daemon running", which
        # `docker --version` alone can't tell apart.
        try:
            result = subprocess.run(  # nosec B603 - fixed argv, shell=False
                [docker_path, "info"],
                capture_output=True,
                text=True,
                timeout=_PROBE_TIMEOUT_SECONDS,
                check=False,
            )
            daemon_running = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            daemon_running = False

    compose_version = None
    if docker_path:
        compose_version = _run([docker_path, "compose", "version"])

    capabilities = [
        _available(
            name="Docker",
            category=CapabilityCategory.DOCKER,
            found=docker_path is not None,
            version=docker_version,
            path=docker_path,
            required=False,
            remediation="Install from https://docs.docker.com/get-docker/",
        )
    ]
    if docker_path:
        capabilities.append(
            EnvironmentCapability(
                name="Docker Daemon",
                category=CapabilityCategory.DOCKER,
                available=daemon_running,
                required=False,
                status=(
                    CapabilityStatus.AVAILABLE if daemon_running else CapabilityStatus.DEGRADED
                ),
                reason=(
                    ""
                    if daemon_running
                    else "Docker CLI is installed but the daemon isn't reachable."
                ),
                remediation="" if daemon_running else "Start Docker Desktop / the docker service.",
            )
        )
        capabilities.append(
            _available(
                name="Docker Compose",
                category=CapabilityCategory.DOCKER,
                found=compose_version is not None,
                version=compose_version,
                required=False,
                remediation="Docker Compose ships with recent Docker Desktop/Engine installs.",
            )
        )
    return capabilities


# --- Git ------------------------------------------------------------------


def detect_git() -> list[EnvironmentCapability]:
    git_path = shutil.which("git")
    git_version = _run([git_path, "--version"]) if git_path else None
    capabilities = [
        _available(
            name="Git",
            category=CapabilityCategory.GIT,
            found=git_path is not None,
            version=git_version,
            path=git_path,
            required=False,
            remediation="Install from https://git-scm.com/downloads",
        )
    ]
    if not git_path:
        return capabilities

    is_repo = _run([git_path, "rev-parse", "--is-inside-work-tree"], cwd=PROJECT_ROOT) == "true"
    if not is_repo:
        capabilities.append(
            EnvironmentCapability(
                name="Git Repository",
                category=CapabilityCategory.GIT,
                available=False,
                required=False,
                status=CapabilityStatus.NOT_REQUIRED,
                reason=f"{PROJECT_ROOT} is not inside a git working tree.",
            )
        )
        return capabilities

    branch = _run([git_path, "branch", "--show-current"], cwd=PROJECT_ROOT) or "(detached HEAD)"
    status_output = _run([git_path, "status", "--porcelain"], cwd=PROJECT_ROOT)
    clean = not status_output
    capabilities.append(
        EnvironmentCapability(
            name="Git Repository",
            category=CapabilityCategory.GIT,
            available=True,
            version=branch,
            required=False,
            status=CapabilityStatus.AVAILABLE,
            reason=f"Branch: {branch}",
        )
    )
    capabilities.append(
        EnvironmentCapability(
            name="Working Tree",
            category=CapabilityCategory.GIT,
            available=clean,
            required=False,
            status=CapabilityStatus.AVAILABLE if clean else CapabilityStatus.DEGRADED,
            reason="Clean" if clean else "Uncommitted changes are present.",
            remediation="" if clean else "Commit or stash changes, or pass --allow-dirty.",
        )
    )
    return capabilities


def detect_all(*, ffmpeg_required: bool = False) -> list[EnvironmentCapability]:
    capabilities: list[EnvironmentCapability] = []
    capabilities.extend(detect_operating_system())
    capabilities.extend(detect_python())
    capabilities.extend(detect_node())
    capabilities.extend(detect_browsers())
    capabilities.append(detect_ffmpeg(required=ffmpeg_required))
    capabilities.extend(detect_docker())
    capabilities.extend(detect_git())
    return capabilities
