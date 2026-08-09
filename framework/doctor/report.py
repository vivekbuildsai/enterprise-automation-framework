"""Browser recommendation + human-readable rendering for a `DoctorReport`
— one formatter shared by the CLI's console output and (eventually) any
other caller, so the two representations of "what did doctor find" can
never drift apart (same precedent as
`framework.sync.test_inventory.format_inventory`).

The browser-recommendation logic encodes a fact that is easy to get
wrong: Playwright's `firefox`/`webkit` engines have **no** `channel`
parameter — unlike `chromium` (which can launch a real system Chrome via
`channel="chrome"` or Edge via `channel="msedge"`), Firefox/Safari
selection in this framework always launches *Playwright's own bundled*
Firefox/WebKit build, never the machine's real Firefox or Safari (Safari
itself cannot be automated at all, on any platform — see
`framework.drivers.browser_factory`). Doctor's recommendation logic must
therefore check the *Playwright-managed* Firefox/WebKit capability, not
the system Firefox executable, when considering `BrowserType.FIREFOX`/
`BrowserType.SAFARI`.
"""

from __future__ import annotations

from framework.doctor.models import (
    CapabilityCategory,
    CapabilityStatus,
    DoctorReport,
    EnvironmentCapability,
)

# BrowserType.value -> the EnvironmentCapability.name that must be
# AVAILABLE for BrowserFactory to actually be able to launch it.
_BROWSER_TYPE_REQUIREMENT: dict[str, str] = {
    "chromium": "Playwright Chromium",
    "edge": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Playwright Firefox",
    "safari": "Playwright WebKit",
}

# Bundled Chromium first (zero extra configuration, this framework's own
# existing default) — Edge next, since a customer environment that
# prohibits bundled Chromium but has Edge available is the scenario this
# milestone was explicitly validated against.
_DEFAULT_PRIORITY: tuple[str, ...] = ("chromium", "edge", "chrome", "firefox", "safari")

_CATEGORY_LABELS: dict[CapabilityCategory, str] = {
    CapabilityCategory.OPERATING_SYSTEM: "Operating System",
    CapabilityCategory.PYTHON: "Python",
    CapabilityCategory.NODE: "Node Ecosystem",
    CapabilityCategory.BROWSER: "Browsers",
    CapabilityCategory.FFMPEG: "FFmpeg",
    CapabilityCategory.DOCKER: "Docker",
    CapabilityCategory.GIT: "Git",
}


def _capability_available(browser_type: str, by_name: dict[str, EnvironmentCapability]) -> bool:
    capability_name = _BROWSER_TYPE_REQUIREMENT.get(browser_type)
    capability = by_name.get(capability_name) if capability_name else None
    return bool(capability and capability.available)


def recommend_browser(
    capabilities: list[EnvironmentCapability], *, requested: str | None = None
) -> tuple[str | None, str]:
    """Returns `(browser_type_value, reason)`. `browser_type_value` is
    `None` whenever no usable engine was found — including when
    `requested` names a real `BrowserType` that just isn't available on
    this machine. Never silently substitutes a different browser than
    what was explicitly requested (see the module docstring's Firefox/
    WebKit note for why "silently fall back to Chromium" would be
    especially wrong here).
    """
    by_name = {c.name: c for c in capabilities}

    if requested:
        if requested not in _BROWSER_TYPE_REQUIREMENT:
            supported = ", ".join(_BROWSER_TYPE_REQUIREMENT)
            return None, f"Unknown browser {requested!r}. Supported: {supported}."
        if _capability_available(requested, by_name):
            capability_name = _BROWSER_TYPE_REQUIREMENT[requested]
            return requested, f"{capability_name} was explicitly requested and is available."
        capability_name = _BROWSER_TYPE_REQUIREMENT[requested]
        capability = by_name.get(capability_name)
        remediation = capability.remediation if capability and capability.remediation else ""
        detail = f" {remediation}" if remediation else ""
        return None, f"{requested} was requested but {capability_name} is unavailable.{detail}"

    for browser_type in _DEFAULT_PRIORITY:
        if _capability_available(browser_type, by_name):
            capability_name = _BROWSER_TYPE_REQUIREMENT[browser_type]
            return browser_type, f"{capability_name} is available (auto-selected)."

    return None, "No usable browser engine was detected. Run: poetry run playwright install"


def apply_not_required_downgrades(
    capabilities: list[EnvironmentCapability], *, selected_browser: str | None
) -> list[EnvironmentCapability]:
    """Once a browser is actually selected, every *other* still-missing,
    non-required browser capability is redisplayed as `NOT_REQUIRED`
    rather than `MISSING` — the judgment doctor's own detectors
    deliberately don't make on their own (see
    `framework.doctor.detectors._available`'s docstring).
    """
    if selected_browser is None:
        return capabilities
    selected_capability_name = _BROWSER_TYPE_REQUIREMENT.get(selected_browser)
    updated: list[EnvironmentCapability] = []
    for capability in capabilities:
        if (
            capability.category == CapabilityCategory.BROWSER
            and capability.name != selected_capability_name
            and not capability.available
            and capability.status == CapabilityStatus.MISSING
        ):
            updated.append(
                capability.model_copy(
                    update={
                        "status": CapabilityStatus.NOT_REQUIRED,
                        "reason": "Not required for the currently selected browser.",
                        "remediation": "",
                    }
                )
            )
        else:
            updated.append(capability)
    return updated


def format_capability_matrix(capabilities: list[EnvironmentCapability]) -> str:
    by_category: dict[CapabilityCategory, list[EnvironmentCapability]] = {}
    for capability in capabilities:
        by_category.setdefault(capability.category, []).append(capability)

    lines: list[str] = []
    for category, label in _CATEGORY_LABELS.items():
        entries = by_category.get(category)
        if not entries:
            continue
        lines.append(f"{label}:")
        for capability in entries:
            status_label = capability.status.value.upper().replace("_", " ")
            detail = f"  {capability.name}: {status_label}"
            if capability.version:
                detail += f" ({capability.version})"
            lines.append(detail)
            if capability.path:
                lines.append(f"    Path: {capability.path}")
            if capability.reason and not capability.available:
                lines.append(f"    Reason: {capability.reason}")
            if capability.remediation:
                lines.append(f"    Remediation: {capability.remediation}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_summary_line(report: DoctorReport) -> str:
    missing_required = report.required_missing
    if missing_required:
        names = ", ".join(c.name for c in missing_required)
        return f"DOCTOR: FAILED — required capability missing: {names}"
    if report.recommended_browser:
        return f"DOCTOR: PASSED — recommended browser: {report.recommended_browser}"
    return "DOCTOR: PASSED"
