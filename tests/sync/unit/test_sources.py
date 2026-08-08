from __future__ import annotations

import subprocess
import zipfile

import pytest

from framework.exceptions import ConfigurationError
from framework.sync import GitRepositorySource, LocalDirectorySource, ZipArchiveSource

pytestmark = pytest.mark.sync


class TestLocalDirectorySource:
    def test_materialize_returns_the_same_directory(self, tmp_path) -> None:
        source = LocalDirectorySource(tmp_path)
        assert source.materialize() == tmp_path

    def test_raises_for_a_non_directory(self, tmp_path) -> None:
        not_a_dir = tmp_path / "missing"
        with pytest.raises(ConfigurationError):
            LocalDirectorySource(not_a_dir)

    def test_cleanup_never_touches_the_caller_directory(self, tmp_path) -> None:
        (tmp_path / "keep.txt").write_text("still here")
        source = LocalDirectorySource(tmp_path)
        source.materialize()
        source.cleanup()
        assert (tmp_path / "keep.txt").exists()


class TestZipArchiveSource:
    def test_extracts_a_well_formed_archive(self, tmp_path) -> None:
        zip_path = tmp_path / "repo.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("src/app.py", "print('hi')")
            archive.writestr("README.md", "# demo")

        source = ZipArchiveSource(zip_path)
        extracted = source.materialize()
        try:
            assert (extracted / "src" / "app.py").read_text() == "print('hi')"
            assert (extracted / "README.md").exists()
        finally:
            source.cleanup()

    def test_rejects_path_traversal_member(self, tmp_path) -> None:
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("../../etc/evil.txt", "pwned")

        source = ZipArchiveSource(zip_path)
        with pytest.raises(ConfigurationError, match="path traversal"):
            source.materialize()

    def test_rejects_absolute_path_member(self, tmp_path) -> None:
        """`Path(root) / "/etc/passwd"` evaluates to `/etc/passwd` in
        Python's pathlib (an absolute right operand replaces the whole
        path) — a zip-slip variant distinct from `../` traversal. The
        containment check must catch this too, not just relative escapes.
        """
        zip_path = tmp_path / "malicious_absolute.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("/etc/passwd", "pwned-absolute")

        source = ZipArchiveSource(zip_path)
        with pytest.raises(ConfigurationError, match="path traversal"):
            source.materialize()

    def test_cleanup_removes_the_extraction_directory(self, tmp_path) -> None:
        zip_path = tmp_path / "repo.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("a.txt", "content")

        source = ZipArchiveSource(zip_path)
        extracted = source.materialize()
        source.cleanup()
        assert not extracted.exists()


@pytest.fixture
def local_git_repo(tmp_path):
    """A real, local git repository — cloning it (via a file-path URL)
    exercises the real `git clone` mechanism `GitRepositorySource` uses,
    without needing network access to a real GitHub/GitLab host.
    """
    repo_dir = tmp_path / "origin_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
    (repo_dir / "app.py").write_text("import pytest\n")
    subprocess.run(["git", "add", "app.py"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_dir, check=True)
    return repo_dir


class TestGitRepositorySource:
    def test_clones_a_real_local_repository(self, local_git_repo) -> None:
        source = GitRepositorySource(str(local_git_repo))
        cloned = source.materialize()
        try:
            assert (cloned / "app.py").exists()
            assert (cloned / ".git").exists()
        finally:
            source.cleanup()

    def test_raises_actionable_error_for_an_invalid_source(self, tmp_path) -> None:
        source = GitRepositorySource(str(tmp_path / "does-not-exist"))
        with pytest.raises(ConfigurationError, match="git clone failed"):
            source.materialize()

    def test_cleanup_removes_the_clone_directory(self, local_git_repo) -> None:
        source = GitRepositorySource(str(local_git_repo))
        cloned = source.materialize()
        source.cleanup()
        assert not cloned.exists()
