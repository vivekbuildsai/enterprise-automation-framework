"""CLI-level coverage for `python -m framework.extension analyze` — the
four customer-choice modes (DISCOVER ONLY has no CLI involvement here;
the other three map to `--mode reuse-analysis`/`extension-plan`/
`ai-recommendations`). Never runs discovery or repository analysis
itself: both input reports are written directly, the same way a real
`python -m framework.discovery`/`python -m framework.sync analyze` run
would have produced them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.discovery.models import DiscoveredNetworkCall, DiscoveredPage, DiscoveryReport
from framework.extension.__main__ import main
from framework.extension.models import ExtensionReport
from framework.sync.models import (
    CapabilityCatalog,
    CapabilityCategory,
    ExistingCapability,
    RepositoryAnalysis,
)

pytestmark = pytest.mark.extension


def _write_sync_report(path: Path) -> None:
    analysis = RepositoryAnalysis(
        source="existing-repo",
        capability_catalog=CapabilityCatalog(
            capabilities=[
                ExistingCapability(
                    category=CapabilityCategory.API_CLIENT,
                    name="EmployeeApi.get_employee",
                    source_file="api/employee_api.py",
                    endpoint_pattern="/employees/{param}",
                    http_method="GET",
                ),
                ExistingCapability(
                    category=CapabilityCategory.AUTHENTICATION,
                    name="JWT",
                    source_file="",
                    evidence="JWT mentioned in repository",
                ),
            ]
        ),
    )
    analysis.save(path)


def _write_discovery_report(path: Path) -> None:
    report = DiscoveryReport(
        source="new-ui",
        pages=[
            DiscoveredPage(
                url="https://example.test/employees/42",
                title="Employee Details",
                network_calls=[
                    DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)
                ],
            )
        ],
    )
    report.save(path)


def test_reuse_analysis_mode_writes_correlations_only(tmp_path: Path, capsys) -> None:
    sync_report = tmp_path / "sync.json"
    discovery_report = tmp_path / "discovery.json"
    output = tmp_path / "extension.json"
    _write_sync_report(sync_report)
    _write_discovery_report(discovery_report)

    exit_code = main(
        [
            "analyze",
            "--discovery-report",
            str(discovery_report),
            "--sync-report",
            str(sync_report),
            "--output",
            str(output),
            "--mode",
            "reuse-analysis",
        ]
    )

    assert exit_code == 0
    report = ExtensionReport.load(output)
    assert report.correlations
    assert report.extension_items == []
    assert report.test_opportunities == []
    assert "correlation" in capsys.readouterr().out.lower()


def test_extension_plan_mode_is_the_default_and_adds_items_and_opportunities(
    tmp_path: Path,
) -> None:
    sync_report = tmp_path / "sync.json"
    discovery_report = tmp_path / "discovery.json"
    output = tmp_path / "extension.json"
    _write_sync_report(sync_report)
    _write_discovery_report(discovery_report)

    exit_code = main(
        [
            "analyze",
            "--discovery-report",
            str(discovery_report),
            "--sync-report",
            str(sync_report),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    report = ExtensionReport.load(output)
    assert report.extension_items
    assert report.test_opportunities
    assert any(item.classification.value == "reuse_existing" for item in report.extension_items)


def test_ai_recommendations_mode_writes_a_separate_ai_output_file(tmp_path: Path) -> None:
    sync_report = tmp_path / "sync.json"
    discovery_report = tmp_path / "discovery.json"
    output = tmp_path / "extension.json"
    ai_output = tmp_path / "ai.json"
    _write_sync_report(sync_report)
    _write_discovery_report(discovery_report)

    exit_code = main(
        [
            "analyze",
            "--discovery-report",
            str(discovery_report),
            "--sync-report",
            str(sync_report),
            "--output",
            str(output),
            "--mode",
            "ai-recommendations",
            "--ai-output",
            str(ai_output),
        ]
    )

    assert exit_code == 0
    assert ai_output.exists()
    recommendations = json.loads(ai_output.read_text(encoding="utf-8"))
    assert isinstance(recommendations, list)
    # The main extension report is still written and unaffected by the AI step.
    report = ExtensionReport.load(output)
    assert report.extension_items


def test_missing_discovery_report_is_a_clean_error_not_a_traceback(tmp_path: Path, capsys) -> None:
    sync_report = tmp_path / "sync.json"
    _write_sync_report(sync_report)

    exit_code = main(
        [
            "analyze",
            "--discovery-report",
            str(tmp_path / "missing.json"),
            "--sync-report",
            str(sync_report),
        ]
    )

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "Error:" in stderr
    assert "Traceback" not in stderr


def test_never_writes_anywhere_but_the_two_declared_output_files(tmp_path: Path) -> None:
    sync_report = tmp_path / "sync.json"
    discovery_report = tmp_path / "discovery.json"
    output = tmp_path / "extension.json"
    _write_sync_report(sync_report)
    _write_discovery_report(discovery_report)
    before = set(tmp_path.iterdir())

    main(
        [
            "analyze",
            "--discovery-report",
            str(discovery_report),
            "--sync-report",
            str(sync_report),
            "--output",
            str(output),
            "--mode",
            "reuse-analysis",
        ]
    )

    after = set(tmp_path.iterdir())
    assert after - before == {output}
