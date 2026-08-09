"""`extension run` — the single-command orchestrator. Every test here
avoids a real browser/network by never passing `--url` (pre-seeding the
discovery report `_discover_or_load_new_ui` would otherwise fetch live)
and avoids touching this repository's real files by treating `tmp_path`
as both `PROJECT_ROOT` (so `resolve_scaffold_output_dir` accepts writes
under it — same pattern `tests/extension/unit/test_scaffold.py` uses) and
the `--output-dir`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from framework.discovery.models import DiscoveredNetworkCall, DiscoveredPage, DiscoveryReport
from framework.doctor.models import CapabilityCategory, CapabilityStatus, EnvironmentCapability
from framework.extension import paths as paths_module
from framework.extension import run as run_module
from framework.extension.models import ExtensionReport

pytestmark = pytest.mark.extension


@pytest.fixture(autouse=True)
def _project_root_is_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths_module, "PROJECT_ROOT", tmp_path)


@pytest.fixture(autouse=True)
def _no_real_git_dirty_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to a clean-tree world — tests that specifically
    exercise the dirty-tree gate override this explicitly.
    """
    monkeypatch.setattr(run_module, "detect_git", lambda: [_working_tree(clean=True)])


def _working_tree(*, clean: bool) -> EnvironmentCapability:
    return EnvironmentCapability(
        name="Working Tree",
        category=CapabilityCategory.GIT,
        available=clean,
        required=False,
        status=CapabilityStatus.AVAILABLE if clean else CapabilityStatus.DEGRADED,
        reason="Clean" if clean else "Uncommitted changes are present.",
        remediation="" if clean else "Commit or stash changes, or pass --allow-dirty.",
    )


def _existing_framework_dir(tmp_path: Path) -> Path:
    framework_dir = tmp_path / "existing-framework"
    framework_dir.mkdir()
    (framework_dir / "app.py").write_text(
        "def get_employee(employee_id):\n    return {'id': employee_id}\n", encoding="utf-8"
    )
    return framework_dir


def _seed_discovery_report(output_dir: Path, *, pages: list[DiscoveredPage]) -> None:
    DiscoveryReport(source="new-ui", pages=pages).save(output_dir / "new_ui_discovery_report.json")


def _base_args(tmp_path: Path, framework_dir: Path, **overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "framework": str(framework_dir),
        "url": None,
        "crawl": False,
        "max_pages": 5,
        "headed": False,
        "network_url_pattern": "**/*",
        "output_dir": str(tmp_path / "extension-output"),
        "skip_doctor": True,
        "scaffold": False,
        "target": None,
        "yes": False,
        "allow_dirty": False,
        "overwrite": False,
        "dry_run": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)  # type: ignore[arg-type]


def _run_with_preseeded_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: argparse.Namespace,
    pages: list[DiscoveredPage],
) -> int:
    """`_timestamped_output_dir` is monkeypatched to a fixed directory so
    the discovery report can be seeded at the exact path
    `_discover_or_load_new_ui` will look for it, before `run()` is called.
    """
    fixed_output_dir = Path(args.output_dir) / "fixed-run"
    fixed_output_dir.mkdir(parents=True)
    _seed_discovery_report(fixed_output_dir, pages=pages)
    monkeypatch.setattr(run_module, "_timestamped_output_dir", lambda _: fixed_output_dir)
    return run_module.run(args)


def _healthy_page() -> DiscoveredPage:
    return DiscoveredPage(
        url="https://example.test/employees/42",
        title="Employee Details",
        network_calls=[
            DiscoveredNetworkCall(
                method="GET", path="/employees/42", status=200, host="example.test"
            )
        ],
    )


def _login_page() -> DiscoveredPage:
    return DiscoveredPage(url="https://example.test/c/portal/login", title="Sign In")


def test_analysis_only_run_succeeds_and_writes_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    args = _base_args(tmp_path, framework_dir)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert exit_code == run_module.EXIT_OK
    output = capsys.readouterr().out
    assert "Discovery quality:" in output
    assert "--scaffold not requested" in output
    report_path = Path(args.output_dir) / "fixed-run" / "extension_report.json"
    assert report_path.exists()
    report = ExtensionReport.load(report_path)
    assert report.network_classification is not None
    assert report.network_classification.summary.application_candidate_count == 1
    assert report.discovery_quality is not None


def test_blocked_discovery_quality_stops_before_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    args = _base_args(tmp_path, framework_dir, scaffold=True, yes=True, allow_dirty=True)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_login_page()])

    assert exit_code == run_module.EXIT_DISCOVERY_BLOCKED
    assert "SAFETY GATE" in capsys.readouterr().out
    scaffold_dir = Path(args.output_dir) / "fixed-run" / "scaffold"
    assert not scaffold_dir.exists()


def test_scaffold_declined_on_non_interactive_stdin_without_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    args = _base_args(tmp_path, framework_dir, scaffold=True, yes=False)
    monkeypatch.setattr(run_module.sys.stdin, "isatty", lambda: False)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert exit_code == run_module.EXIT_SCAFFOLD_DECLINED
    assert "Declined" in capsys.readouterr().out


def test_scaffold_dry_run_never_writes_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    args = _base_args(tmp_path, framework_dir, scaffold=True, yes=True, dry_run=True)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert exit_code == run_module.EXIT_OK
    assert "--dry-run: no files written" in capsys.readouterr().out
    scaffold_dir = Path(args.output_dir) / "fixed-run" / "scaffold"
    assert not scaffold_dir.exists()


def test_scaffold_blocked_by_dirty_git_tree_without_allow_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    monkeypatch.setattr(run_module, "detect_git", lambda: [_working_tree(clean=False)])
    args = _base_args(tmp_path, framework_dir, scaffold=True, yes=True, allow_dirty=False)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert exit_code == run_module.EXIT_GIT_DIRTY
    assert "Refusing to scaffold into a dirty working tree" in capsys.readouterr().out


def test_scaffold_proceeds_with_allow_dirty_and_writes_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    monkeypatch.setattr(run_module, "detect_git", lambda: [_working_tree(clean=False)])
    args = _base_args(tmp_path, framework_dir, scaffold=True, yes=True, allow_dirty=True)

    exit_code = _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert exit_code == run_module.EXIT_OK
    assert "Continuing anyway (--allow-dirty)" in capsys.readouterr().out
    scaffold_dir = Path(args.output_dir) / "fixed-run" / "scaffold"
    assert scaffold_dir.exists()
    assert (scaffold_dir / "extension-manifest.json").exists()


def test_skip_doctor_skips_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    args = _base_args(tmp_path, framework_dir, skip_doctor=True)

    _run_with_preseeded_discovery(tmp_path, monkeypatch, args, [_healthy_page()])

    assert "Preflight: skipped (--skip-doctor)." in capsys.readouterr().out


def test_preflight_failure_returns_environment_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    framework_dir = _existing_framework_dir(tmp_path)
    failing_capability = EnvironmentCapability(
        name="Operating System",
        category=CapabilityCategory.OPERATING_SYSTEM,
        available=False,
        required=True,
        status=CapabilityStatus.MISSING,
    )
    monkeypatch.setattr(run_module, "detect_all", lambda **kwargs: [failing_capability])
    args = _base_args(tmp_path, framework_dir, skip_doctor=False)

    exit_code = run_module.run(args)

    assert exit_code == run_module.EXIT_ENVIRONMENT_FAILURE
    assert "DOCTOR: FAILED" in capsys.readouterr().out
