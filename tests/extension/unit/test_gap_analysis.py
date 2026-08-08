"""Extension gap analysis + test opportunity inventory. The primary
scenario mirrors the governing worked example's extension-report table:
a discovered new UI page is `CREATE_NEW`, its reusable API dependency is
`REUSE_EXISTING`, and authentication is `REUSE_EXISTING` off the existing
framework's already-detected mechanism.
"""

from __future__ import annotations

import pytest

from framework.discovery.models import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredNetworkCall,
    DiscoveredPage,
)
from framework.extension.gap_analysis import build_extension_items, build_test_opportunities
from framework.extension.models import ExtensionClassification, ExtensionSubjectType
from framework.sync.models import CapabilityCatalog, CapabilityCategory, ExistingCapability

pytestmark = pytest.mark.extension


def _employee_api_capability() -> ExistingCapability:
    return ExistingCapability(
        category=CapabilityCategory.API_CLIENT,
        name="EmployeeApi.get_employee",
        source_file="api/employee_api.py",
        endpoint_pattern="/employees/{param}",
        http_method="GET",
        evidence="",
    )


def _employee_page() -> DiscoveredPage:
    return DiscoveredPage(
        url="https://example.test/employees/42",
        title="Employee Details",
        elements=[
            DiscoveredElement(
                tag="button",
                element_type="button",
                text="Save",
                locator=DiscoveredLocator(strategy="test_id", value="save-btn"),
            ),
            DiscoveredElement(
                tag="input",
                element_type="textbox",
                locator=DiscoveredLocator(strategy="css", value="#name"),
            ),
        ],
        network_calls=[DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)],
    )


def test_new_page_with_no_matching_page_object_is_create_new() -> None:
    catalog = CapabilityCatalog(capabilities=[_employee_api_capability()])

    items = build_extension_items([_employee_page()], catalog)

    page_item = next(i for i in items if i.subject_type == ExtensionSubjectType.UI_PAGE)
    assert page_item.classification == ExtensionClassification.CREATE_NEW
    assert page_item.matched_capability is None


def test_page_matching_an_existing_page_object_name_is_reuse_existing() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            _employee_api_capability(),
            ExistingCapability(
                category=CapabilityCategory.PAGE_OBJECT,
                name="EmployeeDetailsPage",
                source_file="pages/employee_details_page.py",
                evidence="class EmployeeDetailsPage",
            ),
        ]
    )

    items = build_extension_items([_employee_page()], catalog)

    page_item = next(i for i in items if i.subject_type == ExtensionSubjectType.UI_PAGE)
    assert page_item.classification == ExtensionClassification.REUSE_EXISTING
    assert page_item.matched_capability is not None
    assert page_item.matched_capability.name == "EmployeeDetailsPage"


def test_discovered_api_call_reusing_existing_capability_is_reuse_existing() -> None:
    catalog = CapabilityCatalog(capabilities=[_employee_api_capability()])

    items = build_extension_items([_employee_page()], catalog)

    api_item = next(i for i in items if i.subject_type == ExtensionSubjectType.API_ENDPOINT)
    assert api_item.classification == ExtensionClassification.REUSE_EXISTING
    assert api_item.matched_capability is not None
    assert api_item.matched_capability.name == "EmployeeApi.get_employee"


def test_discovered_api_call_with_no_match_is_create_new() -> None:
    catalog = CapabilityCatalog(capabilities=[])

    items = build_extension_items([_employee_page()], catalog)

    api_item = next(i for i in items if i.subject_type == ExtensionSubjectType.API_ENDPOINT)
    assert api_item.classification == ExtensionClassification.CREATE_NEW


def test_database_item_only_emitted_when_a_table_actually_correlates() -> None:
    catalog_with_table = CapabilityCatalog(
        capabilities=[
            _employee_api_capability(),
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            ),
        ]
    )
    items = build_extension_items([_employee_page()], catalog_with_table)
    assert any(i.subject_type == ExtensionSubjectType.DATABASE for i in items)

    catalog_without_table = CapabilityCatalog(capabilities=[_employee_api_capability()])
    items_without = build_extension_items([_employee_page()], catalog_without_table)
    database_items = [i for i in items_without if i.subject_type == ExtensionSubjectType.DATABASE]
    assert len(database_items) == 1
    assert database_items[0].subject == "Database infrastructure"
    assert database_items[0].classification == ExtensionClassification.UNKNOWN


def test_authentication_reuses_the_first_detected_mechanism() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.AUTHENTICATION,
                name="JWT",
                source_file="",
                evidence="JWT mentioned in repository",
            )
        ]
    )

    items = build_extension_items([], catalog)

    auth_item = next(i for i in items if i.subject_type == ExtensionSubjectType.AUTHENTICATION)
    assert auth_item.classification == ExtensionClassification.REUSE_EXISTING
    assert auth_item.matched_capability is not None
    assert auth_item.matched_capability.name == "JWT"


def test_authentication_is_unknown_when_nothing_was_ever_detected() -> None:
    items = build_extension_items([], CapabilityCatalog(capabilities=[]))

    auth_item = next(i for i in items if i.subject_type == ExtensionSubjectType.AUTHENTICATION)
    assert auth_item.classification == ExtensionClassification.UNKNOWN
    assert auth_item.matched_capability is None


def test_pages_with_no_network_calls_contribute_no_api_or_database_items() -> None:
    static_page = DiscoveredPage(url="https://example.test/about", title="About")
    catalog = CapabilityCatalog(capabilities=[_employee_api_capability()])

    items = build_extension_items([static_page], catalog)

    assert not any(i.subject_type == ExtensionSubjectType.API_ENDPOINT for i in items)
    database_items = [i for i in items if i.subject_type == ExtensionSubjectType.DATABASE]
    assert len(database_items) == 1
    assert database_items[0].subject == "Database infrastructure"
    assert database_items[0].classification == ExtensionClassification.UNKNOWN


def test_opportunity_includes_validation_and_ui_api_consistency_when_evidenced() -> None:
    opportunities = build_test_opportunities([_employee_page()])

    opportunity = opportunities[0]
    assert opportunity.name == "Employee Details"
    assert "validation" in opportunity.suggested_scenario_types
    assert "ui_api_consistency" in opportunity.suggested_scenario_types
    assert "/employees/42" in opportunity.related_api_paths


def test_opportunity_adds_ui_api_db_consistency_only_when_catalog_correlates_a_table() -> None:
    catalog_with_table = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            )
        ]
    )

    with_catalog = build_test_opportunities([_employee_page()], catalog_with_table)
    assert "ui_api_db_consistency" in with_catalog[0].suggested_scenario_types

    without_catalog = build_test_opportunities([_employee_page()])
    assert "ui_api_db_consistency" not in without_catalog[0].suggested_scenario_types


def test_opportunity_for_a_page_with_no_inputs_or_calls_only_suggests_happy_path() -> None:
    static_page = DiscoveredPage(
        url="https://example.test/about",
        title="About",
        elements=[
            DiscoveredElement(
                tag="a",
                element_type="link",
                text="Contact",
                locator=DiscoveredLocator(strategy="role", value="link", role="link"),
            )
        ],
    )

    opportunities = build_test_opportunities([static_page])

    assert opportunities[0].suggested_scenario_types == ["happy_path"]
