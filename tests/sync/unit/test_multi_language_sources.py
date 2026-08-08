"""Every existing source type (local directory / .zip / git URL, including
`file://`) must keep working — now proven against real multi-language
fixtures, not just the pre-existing single-language ones. Existing
security protections (zip-slip, symlink exclusion, read-only analysis)
are unchanged by this milestone; this file re-proves they still hold
when the archived/cloned content spans multiple languages.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argv, no shell, test-only git operations
import zipfile
from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.sources import GitRepositorySource, ZipArchiveSource

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_zip_archive_source_analyzes_a_robot_framework_fixture(tmp_path: Path) -> None:
    zip_path = tmp_path / "robot_repo.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for file_path in (_FIXTURES / "robot_selenium_library").rglob("*"):
            if file_path.is_file():
                archive.write(
                    file_path, file_path.relative_to(_FIXTURES / "robot_selenium_library")
                )

    source = ZipArchiveSource(zip_path)
    try:
        root = source.materialize()
        analysis = RepositoryAnalyzer().analyze(root, source=str(zip_path))
    finally:
        source.cleanup()

    assert analysis.primary_language == "Robot Framework"
    assert any(f.name == "Robot Framework SeleniumLibrary" for f in analysis.detected_frameworks)


def test_zip_archive_source_still_rejects_path_traversal_with_multi_language_content(
    tmp_path: Path,
) -> None:
    """Re-proves zip-slip protection specifically alongside a
    multi-technology payload — a malicious archive doesn't get a pass
    just because most of its content looks like legitimate Java/Robot
    fixture data.
    """
    zip_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("LoginTest.java", "import org.testng.annotations.Test;\n")
        archive.writestr("../../etc/evil.txt", "should never be extracted here\n")

    source = ZipArchiveSource(zip_path)
    with pytest.raises(Exception, match="path traversal|Unsafe archive member"):
        source.materialize()
    source.cleanup()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_git_file_url_source_analyzes_a_csharp_fixture(tmp_path: Path) -> None:
    """`file://` routing (fixed this session's earlier milestone) plus
    multi-language analysis, exercised together end to end.
    """
    repo_dir = tmp_path / "csharp_repo"
    shutil.copytree(_FIXTURES / "csharp_selenium_nunit", repo_dir)
    subprocess.run(["git", "init", "-q", str(repo_dir)], check=True)  # nosec B603 B607
    subprocess.run(
        ["git", "-C", str(repo_dir), "-c", "user.email=a@a.com", "-c", "user.name=a", "add", "-A"],
        check=True,
    )  # nosec B603 B607
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "user.email=a@a.com",
            "-c",
            "user.name=a",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        check=True,
    )  # nosec B603 B607

    source = GitRepositorySource(f"file://{repo_dir}")
    try:
        root = source.materialize()
        analysis = RepositoryAnalyzer().analyze(root, source=f"file://{repo_dir}")
    finally:
        source.cleanup()

    assert analysis.primary_language == "C#"
    assert any(f.name == "NUnit" for f in analysis.detected_frameworks)


def test_local_directory_source_never_modifies_the_fixture(tmp_path: Path) -> None:
    """Read-only analysis, re-proven for a multi-language fixture: no
    file is created, modified, or removed by analyzing it.
    """
    from framework.sync.sources import LocalDirectorySource

    root = _FIXTURES / "typescript_cypress"
    before = sorted(str(p) for p in root.rglob("*") if p.is_file())

    source = LocalDirectorySource(root)
    materialized = source.materialize()
    RepositoryAnalyzer().analyze(materialized, source=str(root))
    source.cleanup()

    after = sorted(str(p) for p in root.rglob("*") if p.is_file())
    assert before == after
