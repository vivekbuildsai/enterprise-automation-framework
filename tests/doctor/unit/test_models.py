"""`DoctorReport`/`EnvironmentCapability` — the data shape every detector
and CLI test below builds on. `required_missing`/`passed` are the exact
predicate `doctor`'s exit code depends on, so they get direct coverage
here independent of any real machine detection.
"""

from __future__ import annotations

import pytest

from framework.doctor.models import (
    CapabilityCategory,
    CapabilityStatus,
    DoctorReport,
    EnvironmentCapability,
)

pytestmark = pytest.mark.doctor


def _capability(**overrides: object) -> EnvironmentCapability:
    defaults: dict[str, object] = {
        "name": "Python",
        "category": CapabilityCategory.PYTHON,
        "available": True,
        "required": False,
        "status": CapabilityStatus.AVAILABLE,
    }
    defaults.update(overrides)
    return EnvironmentCapability(**defaults)  # type: ignore[arg-type]


def test_passed_is_true_when_no_required_capability_is_missing() -> None:
    report = DoctorReport(
        capabilities=[
            _capability(required=True, available=True, status=CapabilityStatus.AVAILABLE),
            _capability(
                name="Docker", required=False, available=False, status=CapabilityStatus.MISSING
            ),
        ]
    )

    assert report.passed is True
    assert report.required_missing == []


def test_passed_is_false_when_a_required_capability_is_missing() -> None:
    report = DoctorReport(
        capabilities=[
            _capability(
                name="Operating System",
                required=True,
                available=False,
                status=CapabilityStatus.MISSING,
            ),
        ]
    )

    assert report.passed is False
    assert len(report.required_missing) == 1
    assert report.required_missing[0].name == "Operating System"


def test_save_and_load_round_trip(tmp_path) -> None:
    report = DoctorReport(
        capabilities=[_capability()],
        recommended_browser="chromium",
        recommendation_reason="Playwright Chromium is available (auto-selected).",
    )
    path = tmp_path / "doctor_report.json"

    report.save(path)
    loaded = DoctorReport.load(path)

    assert loaded.recommended_browser == "chromium"
    assert len(loaded.capabilities) == 1
    assert loaded.capabilities[0].name == "Python"
