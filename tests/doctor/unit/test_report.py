"""Browser recommendation + rendering — pure functions over
`EnvironmentCapability` lists, so every scenario here is a fixture, never
a real machine probe. The Firefox/WebKit note in `report.py`'s module
docstring (Playwright-managed builds, never the system browser) is the
fact `_BROWSER_TYPE_REQUIREMENT` encodes; these tests pin that mapping
down.
"""

from __future__ import annotations

import pytest

from framework.doctor.models import (
    CapabilityCategory,
    CapabilityStatus,
    DoctorReport,
    EnvironmentCapability,
)
from framework.doctor.report import (
    apply_not_required_downgrades,
    format_capability_matrix,
    format_summary_line,
    recommend_browser,
)

pytestmark = pytest.mark.doctor


def _browser_capability(
    name: str, *, available: bool, status: CapabilityStatus | None = None, remediation: str = ""
) -> EnvironmentCapability:
    resolved_status = status or (
        CapabilityStatus.AVAILABLE if available else CapabilityStatus.MISSING
    )
    return EnvironmentCapability(
        name=name,
        category=CapabilityCategory.BROWSER,
        available=available,
        required=False,
        status=resolved_status,
        remediation=remediation,
    )


def test_auto_select_prefers_chromium_first() -> None:
    capabilities = [
        _browser_capability("Playwright Chromium", available=True),
        _browser_capability("Microsoft Edge", available=True),
    ]

    browser, reason = recommend_browser(capabilities)

    assert browser == "chromium"
    assert "Playwright Chromium" in reason


def test_auto_select_falls_back_to_edge_when_chromium_unavailable() -> None:
    capabilities = [
        _browser_capability("Playwright Chromium", available=False),
        _browser_capability("Microsoft Edge", available=True),
    ]

    browser, reason = recommend_browser(capabilities)

    assert browser == "edge"
    assert "Microsoft Edge" in reason


def test_no_browser_available_returns_none_with_install_hint() -> None:
    capabilities = [_browser_capability("Playwright Chromium", available=False)]

    browser, reason = recommend_browser(capabilities)

    assert browser is None
    assert "playwright install" in reason


def test_explicit_request_for_available_browser_is_honored() -> None:
    capabilities = [_browser_capability("Playwright Firefox", available=True)]

    browser, reason = recommend_browser(capabilities, requested="firefox")

    assert browser == "firefox"
    assert "explicitly requested" in reason


def test_explicit_request_for_unavailable_browser_never_substitutes() -> None:
    capabilities = [
        _browser_capability(
            "Playwright Firefox",
            available=False,
            remediation="poetry run playwright install firefox",
        ),
        _browser_capability("Playwright Chromium", available=True),
    ]

    browser, reason = recommend_browser(capabilities, requested="firefox")

    assert browser is None
    assert "Playwright Firefox" in reason
    assert "poetry run playwright install firefox" in reason


def test_unknown_requested_browser_name_is_rejected() -> None:
    browser, reason = recommend_browser([], requested="netscape")

    assert browser is None
    assert "Unknown browser" in reason


def test_apply_not_required_downgrades_clears_reason_and_remediation() -> None:
    capabilities = [
        _browser_capability("Playwright Chromium", available=True),
        EnvironmentCapability(
            name="Firefox",
            category=CapabilityCategory.BROWSER,
            available=False,
            required=False,
            status=CapabilityStatus.MISSING,
            reason="Firefox was not found on this machine.",
            remediation="Install Firefox.",
        ),
    ]

    downgraded = apply_not_required_downgrades(capabilities, selected_browser="chromium")

    firefox = next(c for c in downgraded if c.name == "Firefox")
    assert firefox.status == CapabilityStatus.NOT_REQUIRED
    assert firefox.reason == "Not required for the currently selected browser."
    assert firefox.remediation == ""


def test_apply_not_required_downgrades_leaves_selected_browser_untouched() -> None:
    capabilities = [_browser_capability("Playwright Chromium", available=True)]

    downgraded = apply_not_required_downgrades(capabilities, selected_browser="chromium")

    assert downgraded[0].status == CapabilityStatus.AVAILABLE


def test_apply_not_required_downgrades_is_a_noop_when_no_browser_selected() -> None:
    capabilities = [_browser_capability("Playwright Chromium", available=False)]

    downgraded = apply_not_required_downgrades(capabilities, selected_browser=None)

    assert downgraded[0].status == CapabilityStatus.MISSING


def test_format_capability_matrix_includes_reason_and_remediation_for_missing() -> None:
    capabilities = [
        EnvironmentCapability(
            name="Docker",
            category=CapabilityCategory.DOCKER,
            available=False,
            required=False,
            status=CapabilityStatus.MISSING,
            reason="Docker was not found.",
            remediation="Install Docker.",
        )
    ]

    matrix = format_capability_matrix(capabilities)

    assert "Docker: MISSING" in matrix
    assert "Reason: Docker was not found." in matrix
    assert "Remediation: Install Docker." in matrix


def test_format_capability_matrix_omits_reason_for_available_capability() -> None:
    capabilities = [_browser_capability("Playwright Chromium", available=True)]

    matrix = format_capability_matrix(capabilities)

    assert "Reason:" not in matrix


def test_format_summary_line_failed_lists_required_missing_names() -> None:
    report = DoctorReport(
        capabilities=[
            EnvironmentCapability(
                name="Operating System",
                category=CapabilityCategory.OPERATING_SYSTEM,
                available=False,
                required=True,
                status=CapabilityStatus.MISSING,
            )
        ]
    )

    line = format_summary_line(report)

    assert line.startswith("DOCTOR: FAILED")
    assert "Operating System" in line


def test_format_summary_line_passed_with_recommended_browser() -> None:
    report = DoctorReport(capabilities=[], recommended_browser="chromium")

    line = format_summary_line(report)

    assert line == "DOCTOR: PASSED — recommended browser: chromium"


def test_format_summary_line_passed_with_no_recommendation() -> None:
    report = DoctorReport(capabilities=[], recommended_browser=None)

    line = format_summary_line(report)

    assert line == "DOCTOR: PASSED"
