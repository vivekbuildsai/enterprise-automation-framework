from __future__ import annotations

import pytest

from framework.sync import RepositoryAnalyzer, SupportLevel

pytestmark = pytest.mark.sync


@pytest.fixture
def sample_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "login_page.py").write_text(
        "from selenium import webdriver\n"
        "class LoginPage:\n"
        "    def login(self):\n"
        "        password = 'hunter2_super_secret'\n"
        "        return webdriver.Chrome()\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_login.py").write_text(
        "import pytest\n\ndef test_login():\n    assert True\n"
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "requirements.txt").write_text("selenium\npytest\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.13-slim\n")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "workflows").mkdir()
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
    return tmp_path


def test_analyze_detects_selenium_and_pytest(sample_repo) -> None:
    analysis = RepositoryAnalyzer().analyze(sample_repo, source=str(sample_repo))

    names = {f.name for f in analysis.detected_frameworks}
    assert "Selenium" in names
    assert "pytest" in names

    selenium = next(f for f in analysis.detected_frameworks if f.name == "Selenium")
    assert selenium.support_level == SupportLevel.PARTIALLY_SUPPORTED


def test_analyze_computes_primary_language(sample_repo) -> None:
    analysis = RepositoryAnalyzer().analyze(sample_repo, source=str(sample_repo))
    assert analysis.primary_language == "Python"


def test_analyze_counts_structure(sample_repo) -> None:
    analysis = RepositoryAnalyzer().analyze(sample_repo, source=str(sample_repo))

    assert analysis.structure.test_files >= 1
    assert analysis.structure.page_object_like_files >= 1
    assert analysis.structure.has_docker is True
    assert analysis.structure.has_ci is True
    assert "requirements.txt" in analysis.structure.dependency_files


def test_analyze_flags_hardcoded_credential_without_leaking_the_value(sample_repo) -> None:
    analysis = RepositoryAnalyzer().analyze(sample_repo, source=str(sample_repo))

    credential_findings = [f for f in analysis.findings if f.category == "hardcoded_credential"]
    assert len(credential_findings) == 1
    assert credential_findings[0].file == "src/login_page.py"
    assert "hunter2_super_secret" not in credential_findings[0].description


def test_analyze_report_round_trips_through_json(sample_repo, tmp_path) -> None:
    analysis = RepositoryAnalyzer().analyze(sample_repo, source=str(sample_repo))
    path = tmp_path / "analysis.json"

    analysis.save(path)
    from framework.sync import RepositoryAnalysis

    loaded = RepositoryAnalysis.load(path)

    assert loaded.primary_language == analysis.primary_language
    assert len(loaded.detected_frameworks) == len(analysis.detected_frameworks)


def test_analyze_never_invents_a_framework_not_present(tmp_path) -> None:
    empty_repo = tmp_path / "empty"
    empty_repo.mkdir()
    (empty_repo / "README.md").write_text("# nothing automation-related here\n")

    analysis = RepositoryAnalyzer().analyze(empty_repo, source=str(empty_repo))

    assert analysis.detected_frameworks == []


def test_analyze_does_not_follow_symlinks_outside_the_repository(tmp_path) -> None:
    """A malicious cloned/extracted repository could contain a symlink
    pointing outside itself (e.g. at a device file or an unrelated local
    file) — `Path.is_file()` follows symlinks by default, so this must be
    excluded explicitly rather than silently read.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    outside_target = tmp_path / "outside_secret.txt"
    outside_target.write_text("password: should-never-be-read\n")
    (repo / "evil_link").symlink_to(outside_target)

    analysis = RepositoryAnalyzer().analyze(repo, source=str(repo))

    assert analysis.structure.total_files == 0
    assert analysis.findings == []
