"""End-to-end, file-system-safe proof of the new-UI extension workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.discovery.models import DiscoveredNetworkCall, DiscoveredPage, DiscoveryReport
from framework.extension.__main__ import main as extension_main
from framework.extension.models import (
    ExtensionClassification,
    ExtensionReport,
    ExtensionSubjectType,
)
from framework.sync import RepositoryAnalyzer

pytestmark = pytest.mark.extension


def test_new_ui_reuses_a_mature_framework_without_modifying_it(tmp_path: Path) -> None:
    """A controlled customer-shaped fixture: existing shared backend assets
    plus a new UI page. The analyzer reads the fixture; only report paths
    outside it are written.
    """
    existing = tmp_path / "existing_framework"
    (existing / "api").mkdir(parents=True)
    (existing / "db").mkdir()
    (existing / "validation").mkdir()
    (existing / "testdata").mkdir()
    (existing / "auth.md").write_text("JWT authentication\n", encoding="utf-8")
    (existing / "api" / "employee_api.py").write_text(
        "class EmployeeApi:\n"
        "    def get_employee(self, employee_id):\n"
        '        return self.client.get(f"/employees/{employee_id}")\n',
        encoding="utf-8",
    )
    (existing / "db" / "employee_repository.py").write_text(
        'class EmployeeRepository:\n    __tablename__ = "employee"\n', encoding="utf-8"
    )
    (existing / "validation" / "employee_validator.py").write_text(
        "class EmployeeValidator:\n    def compare(self): return DataComparator.compare({}, {})\n",
        encoding="utf-8",
    )
    (existing / "testdata" / "employee_factory.py").write_text(
        "class EmployeeFactory: pass\n", encoding="utf-8"
    )
    (existing / "reporting.py").write_text("import allure\n", encoding="utf-8")
    before = {p.relative_to(existing): p.read_bytes() for p in existing.rglob("*") if p.is_file()}

    analysis = RepositoryAnalyzer().analyze(existing, source=str(existing))
    sync_report = tmp_path / "sync.json"
    analysis.save(sync_report)

    discovery_report = tmp_path / "new_ui.json"
    DiscoveryReport(
        source="https://new-ui.example.test",
        pages=[
            DiscoveredPage(
                url="https://new-ui.example.test/employees/42",
                title="New Employee Details",
                network_calls=[
                    DiscoveredNetworkCall(method="GET", path="/employees/42", status=200),
                    DiscoveredNetworkCall(method="GET", path="/departments/7", status=200),
                ],
            )
        ],
    ).save(discovery_report)
    output = tmp_path / "extension.json"

    assert (
        extension_main(
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
        == 0
    )

    report = ExtensionReport.load(output)
    assert any(
        item.subject == "GET /employees/42"
        and item.classification == ExtensionClassification.REUSE_EXISTING
        for item in report.extension_items
    )
    assert any(
        item.subject == "GET /departments/7"
        and item.classification == ExtensionClassification.CREATE_NEW
        for item in report.extension_items
    )
    assert any(
        item.subject_type == ExtensionSubjectType.VALIDATION
        and item.classification == ExtensionClassification.REUSE_EXISTING
        for item in report.extension_items
    )
    assert any(
        item.subject_type == ExtensionSubjectType.TEST_DATA
        and item.classification == ExtensionClassification.REUSE_EXISTING
        for item in report.extension_items
    )
    assert any(
        item.subject_type == ExtensionSubjectType.REPORTING
        and item.classification == ExtensionClassification.REUSE_EXISTING
        for item in report.extension_items
    )
    after = {p.relative_to(existing): p.read_bytes() for p in existing.rglob("*") if p.is_file()}
    assert after == before
