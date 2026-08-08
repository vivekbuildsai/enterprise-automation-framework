"""Execution-model detection — captures the customer's existing test
invocation without ever running it. Every field must trace back to a
real file; nothing is guessed from file-type convention alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.execution_model import detect_execution_model

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def _model_for(fixture_name: str):
    root = _FIXTURES / fixture_name
    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(root)
    contents = analyzer._read_text_files(files)
    return detect_execution_model(contents)


def test_testng_suite_xml_yields_command_runner_and_real_parallelism() -> None:
    model = _model_for("java_selenium_testng")

    assert model is not None
    assert model.command == "mvn test -Dsurefire.suiteXmlFiles=testng.xml"
    assert model.runner == "TestNG (via Maven Surefire)"
    assert model.parallelism == 4
    assert "Allure" in model.reporting


def test_playwright_config_yields_retries_workers_and_browser() -> None:
    model = _model_for("typescript_playwright")

    assert model is not None
    assert model.command == "playwright test"
    assert model.retries == 2
    assert model.parallelism == 4
    assert model.browser == "chromium"
    assert "Allure" in model.reporting
    assert "HTML reporter" in model.reporting


def test_pytest_config_presence_implies_command_when_no_more_specific_evidence_exists() -> None:
    model = _model_for("python_pytest_playwright")

    assert model is not None
    assert model.command == "pytest"
    assert model.retries == 2
    # "-n auto" (no fixed digit) never fabricates a specific parallelism number.
    assert model.parallelism is None


def test_robot_command_extracted_from_readme() -> None:
    model = _model_for("robot_selenium_library")

    assert model is not None
    assert model.command == "robot --outputdir results tests/"


def test_no_evidence_at_all_yields_none_not_an_empty_model(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("nothing relevant here\n")

    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(tmp_path)
    contents = analyzer._read_text_files(files)

    assert detect_execution_model(contents) is None


def test_csproj_presence_alone_never_implies_a_dotnet_test_command() -> None:
    """`.csproj` file *existing* is not evidence of an execution command —
    only a real invocation (CI, script, README) is. This fixture has no
    such evidence, so `command` must stay `None`, never guessed from the
    file extension's convention.
    """
    model = _model_for("csharp_selenium_nunit")

    assert model is None or model.command is None


def test_github_actions_run_step_is_parsed_via_real_yaml(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text(
        "name: CI\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - run: npx playwright test --project=chromium\n"
    )
    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(tmp_path)
    contents = analyzer._read_text_files(files)

    model = detect_execution_model(contents)

    assert model is not None
    assert model.command == "npx playwright test --project=chromium"


def test_testng_xml_entity_expansion_is_never_processed() -> None:
    """A `testng.xml` in an analyzed repository is untrusted input — the
    classic "billion laughs" internal-entity-expansion payload must never
    be expanded (confirmed separately that `xml.etree.ElementTree`, the
    original implementation, *does* expand internal entities by default;
    this is why parallelism extraction was rewritten as a targeted regex
    over just the `<suite ...>` opening tag instead of a general XML
    parse — see the module docstring in execution_model.py).
    """
    malicious = (
        '<?xml version="1.0"?>\n'
        "<!DOCTYPE lolz [\n"
        ' <!ENTITY lol "lol">\n'
        ' <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">\n'
        "]>\n"
        '<suite name="&lol2;" parallel="methods" thread-count="4">\n'
        "</suite>\n"
    )
    model = detect_execution_model({Path("testng.xml"): malicious})

    assert model is not None
    assert model.parallelism == 4  # the real, legitimate attribute — still extracted
    assert model.runner == "TestNG (via Maven Surefire)"


def test_malformed_ci_yaml_does_not_crash(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("this: [is not, valid: yaml\n")

    analyzer = RepositoryAnalyzer()
    files = analyzer._collect_files(tmp_path)
    contents = analyzer._read_text_files(files)

    # Must not raise — malformed CI config degrades gracefully.
    detect_execution_model(contents)
