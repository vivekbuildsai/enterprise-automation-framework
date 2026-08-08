from __future__ import annotations

import pytest

from framework.sync.__main__ import _resolve_source
from framework.sync.sources import GitRepositorySource, LocalDirectorySource, ZipArchiveSource

pytestmark = pytest.mark.sync


class TestResolveSource:
    def test_zip_extension_routes_to_zip_archive_source(self) -> None:
        assert isinstance(_resolve_source("my_repo.zip"), ZipArchiveSource)

    def test_https_url_routes_to_git_repository_source(self) -> None:
        assert isinstance(
            _resolve_source("https://github.com/example/repo.git"), GitRepositorySource
        )

    def test_http_url_routes_to_git_repository_source(self) -> None:
        assert isinstance(
            _resolve_source("http://internal-git.example.com/repo.git"), GitRepositorySource
        )

    def test_ssh_shorthand_routes_to_git_repository_source(self) -> None:
        assert isinstance(_resolve_source("git@github.com:example/repo.git"), GitRepositorySource)

    def test_ssh_url_routes_to_git_repository_source(self) -> None:
        assert isinstance(
            _resolve_source("ssh://git@github.com/example/repo.git"), GitRepositorySource
        )

    def test_file_url_routes_to_git_repository_source(self, tmp_path) -> None:
        """Regression test: `file://` previously fell through to
        `LocalDirectorySource`, which rejects any string that isn't a
        real directory path — producing a confusing "Not a directory"
        error for a source `GitRepositorySource` already documents
        supporting (`git clone` accepts `file://` remotes natively).
        """
        source = _resolve_source(f"file://{tmp_path}")
        assert isinstance(source, GitRepositorySource)

    def test_plain_local_path_routes_to_local_directory_source(self, tmp_path) -> None:
        source = _resolve_source(str(tmp_path))
        assert isinstance(source, LocalDirectorySource)
