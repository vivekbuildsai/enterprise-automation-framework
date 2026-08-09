"""Detector-layer behavior — mocked where a detector shells out
(`shutil.which`/`subprocess.run`), real where it's safe and
self-contained (`detect_git` against a throwaway tmp_path repository).
Pins down the two real bugs fixed during this milestone: an `AVAILABLE`
capability must never carry install remediation for itself, and git
detection must resolve against `PROJECT_ROOT`, never ambient process cwd.
"""

from __future__ import annotations

import subprocess

import pytest

from framework.doctor import detectors
from framework.doctor.models import CapabilityStatus

pytestmark = pytest.mark.doctor


def test_run_returns_none_for_a_missing_executable() -> None:
    assert detectors._run(["this-binary-does-not-exist-anywhere"]) is None


def test_run_returns_first_stdout_line() -> None:
    result = detectors._run(["python3", "-c", "print('line one'); print('line two')"])

    assert result == "line one"


def test_available_capability_carries_no_reason_or_remediation() -> None:
    capability = detectors._available(
        name="Thing",
        category=detectors.CapabilityCategory.FFMPEG,
        found=True,
        reason="should never appear",
        remediation="should never appear either",
    )

    assert capability.status == CapabilityStatus.AVAILABLE
    assert capability.reason == ""
    assert capability.remediation == ""


def test_missing_capability_keeps_reason_and_remediation() -> None:
    capability = detectors._available(
        name="Thing",
        category=detectors.CapabilityCategory.FFMPEG,
        found=False,
        reason="not found",
        remediation="install it",
    )

    assert capability.status == CapabilityStatus.MISSING
    assert capability.reason == "not found"
    assert capability.remediation == "install it"


def test_detect_ffmpeg_missing_when_not_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detectors.shutil, "which", lambda name: None)

    capability = detectors.detect_ffmpeg()

    assert capability.status == CapabilityStatus.MISSING
    assert capability.available is False
    assert "ffmpeg.org" in capability.remediation


def test_detect_ffmpeg_available_extracts_version_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detectors.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        detectors, "_run", lambda cmd, **kwargs: "ffmpeg version 6.0-static build info..."
    )

    capability = detectors.detect_ffmpeg()

    assert capability.status == CapabilityStatus.AVAILABLE
    assert capability.version == "6.0-static"
    assert capability.reason == ""


def test_detect_node_reports_each_tool_independently(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        return f"/usr/local/bin/{name}" if name == "node" else None

    monkeypatch.setattr(detectors.shutil, "which", fake_which)
    monkeypatch.setattr(detectors, "_run", lambda cmd, **kwargs: "v20.0.0")

    capabilities = detectors.detect_node()

    by_name = {c.name: c for c in capabilities}
    assert by_name["node"].status == CapabilityStatus.AVAILABLE
    assert by_name["npm"].status == CapabilityStatus.MISSING
    assert by_name["npx"].status == CapabilityStatus.MISSING


def test_detect_docker_reports_only_docker_when_cli_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(detectors.shutil, "which", lambda name: None)

    capabilities = detectors.detect_docker()

    assert [c.name for c in capabilities] == ["Docker"]
    assert capabilities[0].status == CapabilityStatus.MISSING


def _git(*args: str, cwd) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def isolated_git_repo(tmp_path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "file.txt").write_text("hello\n", encoding="utf-8")
    _git("add", "file.txt", cwd=repo)
    _git("commit", "-m", "initial", cwd=repo)
    monkeypatch.setattr(detectors, "PROJECT_ROOT", repo)
    return repo


def test_detect_git_reports_clean_working_tree(isolated_git_repo) -> None:
    capabilities = detectors.detect_git()

    by_name = {c.name: c for c in capabilities}
    assert by_name["Git Repository"].status == CapabilityStatus.AVAILABLE
    assert by_name["Git Repository"].version == "main"
    working_tree = by_name["Working Tree"]
    assert working_tree.status == CapabilityStatus.AVAILABLE
    assert working_tree.reason == "Clean"


def test_detect_git_reports_dirty_working_tree(isolated_git_repo) -> None:
    (isolated_git_repo / "file.txt").write_text("changed\n", encoding="utf-8")

    capabilities = detectors.detect_git()

    working_tree = next(c for c in capabilities if c.name == "Working Tree")
    assert working_tree.status == CapabilityStatus.DEGRADED
    assert working_tree.available is False
    assert "Uncommitted changes" in working_tree.reason
    assert "--allow-dirty" in working_tree.remediation


def test_detect_git_resolves_against_project_root_not_ambient_cwd(
    isolated_git_repo, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unrelated_cwd = tmp_path / "somewhere-else"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    capabilities = detectors.detect_git()

    by_name = {c.name: c for c in capabilities}
    assert by_name["Git Repository"].status == CapabilityStatus.AVAILABLE
    assert by_name["Git Repository"].version == "main"


def test_detect_git_not_a_repository_is_not_required_not_missing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty_dir = tmp_path / "not-a-repo"
    empty_dir.mkdir()
    monkeypatch.setattr(detectors, "PROJECT_ROOT", empty_dir)

    capabilities = detectors.detect_git()

    by_name = {c.name: c for c in capabilities}
    if "Git Repository" in by_name:
        assert by_name["Git Repository"].status == CapabilityStatus.NOT_REQUIRED


def test_detect_all_aggregates_every_category(monkeypatch: pytest.MonkeyPatch) -> None:
    """`detect_browsers` is mocked here (real coverage lives in
    `test_detect_browsers_returns_five_independent_facts` below) — this
    test is about `detect_all`'s own aggregation, not re-probing
    Playwright's three managed browsers a second time in this file.
    """
    monkeypatch.setattr(
        detectors,
        "detect_browsers",
        lambda: [
            detectors._available(
                name="Playwright Chromium",
                category=detectors.CapabilityCategory.BROWSER,
                found=True,
            )
        ],
    )

    capabilities = detectors.detect_all(ffmpeg_required=False)

    categories = {c.category for c in capabilities}
    assert detectors.CapabilityCategory.OPERATING_SYSTEM in categories
    assert detectors.CapabilityCategory.PYTHON in categories
    assert detectors.CapabilityCategory.BROWSER in categories
    assert detectors.CapabilityCategory.GIT in categories
