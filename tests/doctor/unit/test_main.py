"""CLI-level coverage for `python -m framework doctor`. Only one test
(`test_default_run_prints_summary_and_returns_an_int_exit_code`) exercises
real machine detection end-to-end — every other test mocks `detect_all`
with a small, deterministic capability fixture. `detect_all` launches
three separate `sync_playwright()` probes (Chromium/Firefox/WebKit); one
real invocation is enough to prove the CLI is wired correctly, and
avoiding the other ~15 real invocations this file used to make (one per
test) is what keeps this suite from leaking Playwright asyncio task/event
loop state into unrelated tests later in the same pytest process (the
concrete symptom: `tests/network/unit/test_network_interception.py`
intermittently failing only when run after this file, never in
isolation) — see docs/Troubleshooting.md if this class of flake resurfaces.

`--fix` is the only path with a real filesystem side effect (writing
`.env`), so those tests also monkeypatch `PROJECT_ROOT` to a `tmp_path`.
"""

from __future__ import annotations

import pytest

from framework.doctor import __main__ as doctor_main
from framework.doctor import env_writer
from framework.doctor.__main__ import main
from framework.doctor.models import (
    CapabilityCategory,
    CapabilityStatus,
    DoctorReport,
    EnvironmentCapability,
)

pytestmark = pytest.mark.doctor


def _fake_capabilities() -> list[EnvironmentCapability]:
    return [
        EnvironmentCapability(
            name="Operating System",
            category=CapabilityCategory.OPERATING_SYSTEM,
            available=True,
            required=True,
            status=CapabilityStatus.AVAILABLE,
        ),
        EnvironmentCapability(
            name="Python",
            category=CapabilityCategory.PYTHON,
            available=True,
            required=True,
            status=CapabilityStatus.AVAILABLE,
        ),
        EnvironmentCapability(
            name="Playwright Chromium",
            category=CapabilityCategory.BROWSER,
            available=True,
            required=False,
            status=CapabilityStatus.AVAILABLE,
        ),
    ]


@pytest.fixture(autouse=True)
def _mock_detect_all(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file gets a fast, deterministic capability list
    unless it opts out via `@pytest.mark.real_detection` — see the module
    docstring for why real `sync_playwright()` invocations are kept to a
    minimum here.
    """
    if "real_detection" in request.keywords:
        return
    monkeypatch.setattr(doctor_main, "detect_all", lambda **kwargs: _fake_capabilities())


@pytest.mark.real_detection
def test_default_run_prints_summary_and_returns_an_int_exit_code(capsys) -> None:
    exit_code = main([])

    out = capsys.readouterr().out
    assert "DOCTOR:" in out
    assert "Recommended browser:" in out
    assert exit_code in (0, 3)


def test_check_flag_behaves_identically_to_default(capsys) -> None:
    exit_code = main(["--check"])

    assert exit_code == 0
    assert "DOCTOR:" in capsys.readouterr().out


def test_report_flag_writes_a_loadable_json_report(tmp_path, capsys) -> None:
    report_path = tmp_path / "doctor_report.json"

    main(["--report", str(report_path)])

    assert report_path.exists()
    loaded = DoctorReport.load(report_path)
    assert loaded.capabilities
    assert f"saved to {report_path}" in capsys.readouterr().out


def test_unknown_browser_choice_is_rejected_by_argparse() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--browser", "netscape"])

    assert exc_info.value.code == 2


def test_fix_dry_run_never_writes_env_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(env_writer, "PROJECT_ROOT", tmp_path)

    main(["--fix", "--dry-run"])

    assert not (tmp_path / ".env").exists()
    assert "--dry-run: no files were written." in capsys.readouterr().out


def test_fix_writes_automation_browser_when_a_browser_is_recommended(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(env_writer, "PROJECT_ROOT", tmp_path)

    exit_code = main(["--fix"])

    env_file = tmp_path / ".env"
    assert env_file.exists()
    assert "AUTOMATION_BROWSER=chromium" in env_file.read_text(encoding="utf-8")
    assert exit_code == 0


def test_fix_is_idempotent_on_a_second_run(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(env_writer, "PROJECT_ROOT", tmp_path)

    main(["--fix"])
    capsys.readouterr()

    main(["--fix"])
    second_out = capsys.readouterr().out

    assert "already set to" in second_out
