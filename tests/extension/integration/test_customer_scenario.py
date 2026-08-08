"""End-to-end customer scenario: an existing, mature framework with TWO
existing UIs (Support Portal, Admin Portal) sharing one API layer, one
database, one authentication mechanism, and one validation layer — plus a
brand-new THIRD UI ("Employee Portal") with zero automation today.

Exercises the full pipeline this milestone built, start to finish:

    RepositoryAnalyzer.analyze() [static, read-only]
        -> CapabilityCatalog (API/DB/auth/validation/test-data/reporting)
    UIDiscoveryEngine.discover_page(capture_network=True) [local, controlled]
        -> DiscoveryReport with shape-only DiscoveredNetworkCall entries
    framework.extension.correlate_network_calls / correlate_database_usage
        -> UIAPICorrelation
    framework.extension.build_extension_items / build_test_opportunities
        -> ExtensionReport body
    framework.extension.recommend_for_ambiguous_items (DisabledProvider)
        -> deterministic "no AI opinion available" recommendations

The "existing framework" fixture (`tests/extension/fixtures/
multi_ui_existing_framework/`) is sanitized, synthetic, and never
imported/executed — `RepositoryAnalyzer` is a static text scanner (see
`framework.sync.analyzer`), so nothing in this test ever runs a line of
fixture source. The "new UI" is a local, controlled Playwright target
(`page.route`), never a real/remote application.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

from framework.ai import DisabledProvider
from framework.discovery.ui_discovery import UIDiscoveryEngine
from framework.extension import (
    ExtensionClassification,
    RelationshipStatus,
    build_extension_items,
    build_test_opportunities,
    correlate_network_calls,
    recommend_for_ambiguous_items,
)
from framework.sync.analyzer import RepositoryAnalyzer

pytestmark = [pytest.mark.integration, pytest.mark.extension]

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_EXISTING_FRAMEWORK_ROOT = _FIXTURES / "multi_ui_existing_framework"

# The UI page lives under /app/ (a UI route); the endpoints it calls live
# under /employees/ and /reports/ (API routes) — kept on distinct path
# shapes on purpose so the page's own document response never accidentally
# collides with, or gets shadowed by, the mocked API routes below.
_NEW_UI_PAGE_URL = "https://employee-portal.test/app/employee-details"


def _discover_new_employee_portal(page: Page):
    """A local, controlled target standing in for a real customer's new,
    zero-test UI — served entirely via `page.route`, never a real network
    call. Calls one endpoint the existing framework already has
    (`GET /employees/42`, matching `EmployeeApi.get_employee`) and one it
    genuinely does not (`POST /reports/custom-export`), so the pipeline has
    a real REUSE_EXISTING case and a real CREATE_NEW case to distinguish.
    """
    page.route(
        _NEW_UI_PAGE_URL,
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body=(
                "<html><body>"
                "<button data-testid='export-btn'>Export</button>"
                "<input id='notes' name='notes' />"
                "<script>"
                "fetch('/employees/42');"
                "fetch('/reports/custom-export', {method: 'POST', "
                "headers: {'Content-Type': 'application/json'}, "
                "body: JSON.stringify({format: 'pdf'})});"
                "</script>"
                "</body></html>"
            ),
        ),
    )
    page.route(
        "https://employee-portal.test/employees/**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id": 42, "name": "Ada Lovelace"}',
        ),
    )
    page.route(
        "https://employee-portal.test/reports/custom-export",
        lambda route: route.fulfill(status=202, content_type="application/json", body="{}"),
    )

    return UIDiscoveryEngine(page).discover_page(_NEW_UI_PAGE_URL, capture_network=True)


def test_capability_catalog_reflects_capabilities_shared_across_both_existing_uis() -> None:
    """Requirement: never assume one UI = one API = one DB = one framework
    — the shared API/DB/auth/validation capabilities must show up in the
    catalog regardless of which existing UI folder was scanned alongside
    them.
    """
    analysis = RepositoryAnalyzer().analyze(
        _EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework"
    )
    names = {c.name for c in analysis.capability_catalog.capabilities}

    assert "EmployeeApi.get_employee" in names
    assert "table:employee" in names
    assert "EmployeeValidator" in names
    assert "SupportTicketPage" in names
    assert "AdminDashboardPage" in names


def test_full_pipeline_reuses_the_existing_employee_endpoint_and_flags_the_new_one(
    page: Page,
) -> None:
    analysis = RepositoryAnalyzer().analyze(
        _EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework"
    )
    catalog = analysis.capability_catalog

    new_ui_page = _discover_new_employee_portal(page)
    calls = new_ui_page.network_calls
    assert {c.path for c in calls} == {
        "/app/employee-details",
        "/employees/42",
        "/reports/custom-export",
    }

    correlations = correlate_network_calls(calls, catalog)
    by_path = {c.discovered_call.path: c for c in correlations}

    assert by_path["/employees/42"].status is RelationshipStatus.LIKELY_REUSABLE
    assert by_path["/employees/42"].matched_capability is not None
    assert by_path["/employees/42"].matched_capability.name == "EmployeeApi.get_employee"

    assert by_path["/reports/custom-export"].status is RelationshipStatus.NOT_FOUND
    assert by_path["/reports/custom-export"].matched_capability is None

    assert by_path["/app/employee-details"].status is RelationshipStatus.NOT_FOUND


def test_extension_report_body_matches_the_governing_worked_example_shape(page: Page) -> None:
    """Mirrors the governing worked example's extension-report table:
    the reusable employee dependency is REUSE_EXISTING, the genuinely new
    dependency is CREATE_NEW, and shared infrastructure (auth/DB/
    validation/test-data/reporting) is REUSE_EXISTING off real evidence —
    all without modifying the existing framework or the new UI.
    """
    analysis = RepositoryAnalyzer().analyze(
        _EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework"
    )
    catalog = analysis.capability_catalog

    new_ui_page = _discover_new_employee_portal(page)
    items = build_extension_items([new_ui_page], catalog)
    by_subject = {item.subject: item for item in items}

    assert by_subject["GET /employees/42"].classification == ExtensionClassification.REUSE_EXISTING
    assert (
        by_subject["POST /reports/custom-export"].classification
        == ExtensionClassification.CREATE_NEW
    )
    assert (
        by_subject["GET /app/employee-details"].classification == ExtensionClassification.CREATE_NEW
    )
    assert by_subject["Authentication"].classification == ExtensionClassification.REUSE_EXISTING
    assert (
        by_subject["Database infrastructure"].classification
        == ExtensionClassification.REUSE_EXISTING
    )
    assert by_subject["Validation"].classification == ExtensionClassification.REUSE_EXISTING
    assert by_subject["Test data"].classification == ExtensionClassification.REUSE_EXISTING
    assert by_subject["Reporting"].classification == ExtensionClassification.REUSE_EXISTING

    # The employee endpoint's data ultimately reaches a known table too —
    # EXTEND_EXISTING, not REUSE_EXISTING, since a table-name path-segment
    # match is weaker evidence than an exact API endpoint+method match.
    assert (
        by_subject["Data behind GET /employees/42"].classification
        == ExtensionClassification.EXTEND_EXISTING
    )


def test_test_opportunity_inventory_covers_the_new_page_without_inventing_test_cases(
    page: Page,
) -> None:
    analysis = RepositoryAnalyzer().analyze(
        _EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework"
    )
    new_ui_page = _discover_new_employee_portal(page)

    opportunities = build_test_opportunities([new_ui_page], analysis.capability_catalog)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert "validation" in opportunity.suggested_scenario_types
    assert "ui_api_consistency" in opportunity.suggested_scenario_types
    assert "ui_api_db_consistency" in opportunity.suggested_scenario_types
    assert set(opportunity.related_api_paths) == {
        "/app/employee-details",
        "/employees/42",
        "/reports/custom-export",
    }


def test_ai_layer_adds_nothing_when_the_deterministic_pass_resolved_everything(
    page: Page,
) -> None:
    """With AI disabled (the default, `DisabledProvider`), the pipeline
    must still run deterministically end to end. In this scenario every
    item resolves outright (REUSE_EXISTING/EXTEND_EXISTING/CREATE_NEW) —
    nothing lands in MANUAL_REVIEW/UNKNOWN — so the optional AI layer must
    produce zero recommendations, proving "AI assists ambiguous mappings"
    holds even against real discovery + real correlation data, not just
    synthetic unit fixtures engineered to be ambiguous.
    """
    analysis = RepositoryAnalyzer().analyze(
        _EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework"
    )
    new_ui_page = _discover_new_employee_portal(page)
    items = build_extension_items([new_ui_page], analysis.capability_catalog)

    recommendations = recommend_for_ambiguous_items(items, DisabledProvider())

    assert recommendations == []


def test_repository_analyzer_never_imports_or_executes_the_fixture_source() -> None:
    """`RepositoryAnalyzer` is a static text scanner (see
    `framework.sync.analyzer`) — it must never `import` anything from the
    scanned repository. If it did, `EmployeeApi`/`EmployeeRepository`/etc.
    would be real Python objects in `sys.modules` after analysis; they
    must not be.
    """
    RepositoryAnalyzer().analyze(_EXISTING_FRAMEWORK_ROOT, source="multi-ui-existing-framework")

    assert not any("employee_api" in name for name in sys.modules)
    assert not any("employee_repository" in name for name in sys.modules)
