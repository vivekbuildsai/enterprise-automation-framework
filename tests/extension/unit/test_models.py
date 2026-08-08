"""Model-level tests for `framework.extension` — the bridging layer between
the existing-framework capability catalog (`framework.sync`) and new-UI
discovery (`framework.discovery`). No correlation logic lives here yet
(see `framework.extension.correlation`, task #182); this only verifies the
models construct, default, and round-trip through JSON correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    RelationshipStatus,
    TestOpportunity,
    UIAPICorrelation,
)
from framework.sync.models import CapabilityCategory, ExistingCapability

pytestmark = pytest.mark.extension


def _employee_get_capability() -> ExistingCapability:
    return ExistingCapability(
        category=CapabilityCategory.API_CLIENT,
        name="EmployeeApi.get_employee",
        source_file="api/employee_api.py",
        endpoint_pattern="/employees/{param}",
        http_method="GET",
        evidence='self._client.get(f"/employees/{employee_id}")',
    )


def _employee_network_call() -> DiscoveredNetworkCall:
    return DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)


def test_ui_api_correlation_reports_a_reusable_match_with_evidence() -> None:
    correlation = UIAPICorrelation(
        discovered_call=_employee_network_call(),
        matched_capability=_employee_get_capability(),
        status=RelationshipStatus.LIKELY_REUSABLE,
        evidence=["endpoint pattern match", "HTTP method match"],
    )

    assert correlation.matched_capability is not None
    assert correlation.matched_capability.name == "EmployeeApi.get_employee"
    assert correlation.status is RelationshipStatus.LIKELY_REUSABLE
    assert len(correlation.evidence) == 2


def test_ui_api_correlation_not_found_has_no_matched_capability() -> None:
    correlation = UIAPICorrelation(
        discovered_call=DiscoveredNetworkCall(method="GET", path="/reports/quarterly", status=200),
        status=RelationshipStatus.NOT_FOUND,
        evidence=[],
    )

    assert correlation.matched_capability is None
    assert correlation.status is RelationshipStatus.NOT_FOUND


def test_extension_item_reuse_existing_points_at_the_reused_capability() -> None:
    item = ExtensionItem(
        subject="Employee API",
        subject_type=ExtensionSubjectType.API_ENDPOINT,
        classification=ExtensionClassification.REUSE_EXISTING,
        matched_capability=_employee_get_capability(),
        reason="Discovered GET /employees/42 matches EmployeeApi.get_employee() exactly.",
        evidence=["endpoint pattern match", "HTTP method match"],
    )

    assert item.classification is ExtensionClassification.REUSE_EXISTING
    assert item.matched_capability is not None


def test_extension_item_create_new_has_no_matched_capability_by_default() -> None:
    item = ExtensionItem(
        subject="New UI component",
        subject_type=ExtensionSubjectType.UI_COMPONENT,
        classification=ExtensionClassification.CREATE_NEW,
        reason="No existing Page Object or component matches this discovered UI element.",
    )

    assert item.matched_capability is None
    assert item.evidence == []


def test_test_opportunity_holds_advisory_scenario_types_only() -> None:
    opportunity = TestOpportunity(
        name="Employee Search",
        page_url="https://example.test/employees",
        related_elements=["role:link Search", "test_id:search-input"],
        related_api_paths=["/employees/search"],
        suggested_scenario_types=["happy_path", "ui_api_consistency"],
    )

    assert opportunity.name == "Employee Search"
    assert "ui_api_consistency" in opportunity.suggested_scenario_types


def test_extension_report_defaults_are_empty_not_none() -> None:
    report = ExtensionReport()

    assert report.correlations == []
    assert report.extension_items == []
    assert report.test_opportunities == []


def test_extension_report_round_trips_through_json(tmp_path: Path) -> None:
    report = ExtensionReport(
        existing_framework_source="existing-repo",
        new_ui_source="new-ui-repo",
        correlations=[
            UIAPICorrelation(
                discovered_call=_employee_network_call(),
                matched_capability=_employee_get_capability(),
                status=RelationshipStatus.LIKELY_REUSABLE,
                evidence=["endpoint pattern match"],
            )
        ],
        extension_items=[
            ExtensionItem(
                subject="Employee API",
                subject_type=ExtensionSubjectType.API_ENDPOINT,
                classification=ExtensionClassification.REUSE_EXISTING,
                matched_capability=_employee_get_capability(),
                reason="Matches existing EmployeeApi.get_employee().",
            )
        ],
        test_opportunities=[
            TestOpportunity(name="Employee Search", page_url="https://example.test/employees")
        ],
    )
    path = tmp_path / "extension_report.json"

    report.save(path)
    loaded = ExtensionReport.load(path)

    assert loaded == report
