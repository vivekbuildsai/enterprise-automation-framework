"""UI/API/database correlation — the core "does an existing capability
already cover this new-UI dependency?" matching logic. The primary
scenario mirrors the governing worked example exactly: a new UI's
discovered `GET /employees/42` against an existing `EmployeeApi.get_employee()`
API client method yields `LIKELY_REUSABLE` with endpoint + method match
evidence.
"""

from __future__ import annotations

import pytest

from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.correlation import (
    correlate_database_usage,
    correlate_network_call,
    correlate_network_calls,
)
from framework.extension.models import RelationshipStatus, UIAPICorrelation
from framework.sync.models import (
    CapabilityCatalog,
    CapabilityCategory,
    ExistingCapability,
)

pytestmark = pytest.mark.extension


def _capability(**overrides: object) -> ExistingCapability:
    defaults: dict[str, object] = {
        "category": CapabilityCategory.API_CLIENT,
        "name": "EmployeeApi.get_employee",
        "source_file": "api/employee_api.py",
        "endpoint_pattern": "/employees/{param}",
        "http_method": "GET",
        "evidence": "",
    }
    defaults.update(overrides)
    return ExistingCapability(**defaults)  # type: ignore[arg-type]


def test_worked_example_get_employee_matches_by_id_yields_likely_reusable() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability()])
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.LIKELY_REUSABLE
    assert correlation.matched_capability is not None
    assert correlation.matched_capability.name == "EmployeeApi.get_employee"
    assert "endpoint pattern match" in correlation.evidence
    assert "HTTP method match" in correlation.evidence


def test_exact_literal_path_match_adds_extra_evidence() -> None:
    catalog = CapabilityCatalog(
        capabilities=[_capability(name="EmployeeApi.search", endpoint_pattern="/employees/search")]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/search", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.LIKELY_REUSABLE
    assert "exact literal path match" in correlation.evidence


def test_endpoint_matches_but_http_method_differs_is_only_possibly_reusable() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability(http_method="GET")])
    call = DiscoveredNetworkCall(method="DELETE", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.POSSIBLY_REUSABLE
    assert correlation.matched_capability is not None
    assert any("HTTP method differs" in e for e in correlation.evidence)


def test_no_matching_capability_at_all_is_not_found() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability()])
    call = DiscoveredNetworkCall(method="GET", path="/invoices/99", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.NOT_FOUND
    assert correlation.matched_capability is None


def test_two_capabilities_matching_both_signals_is_manual_review_not_a_guess() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            _capability(name="EmployeeApi.get_employee", source_file="a.py"),
            _capability(name="LegacyEmployeeClient.get", source_file="b.py"),
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.MANUAL_REVIEW
    assert correlation.matched_capability is None


def test_non_api_capability_is_never_matched_as_an_api_reuse_candidate() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            )
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.NOT_FOUND


def test_correlate_network_calls_preserves_order_and_count() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability()])
    calls = [
        DiscoveredNetworkCall(method="GET", path="/employees/1", status=200),
        DiscoveredNetworkCall(method="GET", path="/invoices/1", status=200),
    ]

    correlations = correlate_network_calls(calls, catalog)

    assert [c.discovered_call.path for c in correlations] == ["/employees/1", "/invoices/1"]
    assert correlations[0].status is RelationshipStatus.LIKELY_REUSABLE
    assert correlations[1].status is RelationshipStatus.NOT_FOUND


def test_correlate_database_usage_matches_plural_path_segment_to_singular_table() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            )
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlations = correlate_database_usage([call], catalog)

    assert correlations[0].status is RelationshipStatus.POSSIBLY_REUSABLE
    assert correlations[0].matched_capability is not None
    assert correlations[0].matched_capability.name == "table:employee"


def test_correlate_database_usage_with_no_matching_table_is_not_found() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            )
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/invoices/42", status=200)

    correlations = correlate_database_usage([call], catalog)

    assert correlations[0].status is RelationshipStatus.NOT_FOUND
    assert correlations[0].matched_capability is None


def test_correlate_database_usage_ambiguous_path_is_manual_review() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            ),
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:department",
                source_file="db/models.py",
            ),
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employee/department", status=200)

    correlations = correlate_database_usage([call], catalog)

    assert correlations[0].status is RelationshipStatus.MANUAL_REVIEW


def test_exact_literal_match_has_higher_confidence_than_pattern_and_method_match() -> None:
    catalog = CapabilityCatalog(
        capabilities=[_capability(name="EmployeeApi.search", endpoint_pattern="/employees/search")]
    )
    exact_call = DiscoveredNetworkCall(method="GET", path="/employees/search", status=200)
    pattern_call_catalog = CapabilityCatalog(capabilities=[_capability()])
    pattern_call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    exact_correlation = correlate_network_call(exact_call, catalog)
    pattern_correlation = correlate_network_call(pattern_call, pattern_call_catalog)

    assert exact_correlation.confidence == 100
    assert pattern_correlation.confidence == 90
    assert exact_correlation.confidence > pattern_correlation.confidence


def test_http_method_mismatch_has_lower_confidence_than_full_match() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability(http_method="GET")])
    call = DiscoveredNetworkCall(method="DELETE", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert 0 < correlation.confidence < 90


def test_manual_review_confidence_is_low() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            _capability(name="EmployeeApi.get_employee", source_file="a.py"),
            _capability(name="LegacyEmployeeClient.get", source_file="b.py"),
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.confidence <= 30


def test_not_found_confidence_is_a_confident_negative_not_zero() -> None:
    catalog = CapabilityCatalog(capabilities=[_capability()])
    call = DiscoveredNetworkCall(method="GET", path="/invoices/99", status=200)

    correlation = correlate_network_call(call, catalog)

    assert correlation.status is RelationshipStatus.NOT_FOUND
    assert correlation.confidence > 0


def test_database_table_match_confidence_is_moderate() -> None:
    catalog = CapabilityCatalog(
        capabilities=[
            ExistingCapability(
                category=CapabilityCategory.DATABASE_UTILITY,
                name="table:employee",
                source_file="db/models.py",
            )
        ]
    )
    call = DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)

    correlations = correlate_database_usage([call], catalog)

    assert 0 < correlations[0].confidence < 90


def test_default_confidence_is_zero_for_a_correlation_built_without_one() -> None:
    correlation = UIAPICorrelation(
        discovered_call=DiscoveredNetworkCall(method="GET", path="/x", status=200),
        status=RelationshipStatus.NOT_FOUND,
    )

    assert correlation.confidence == 0
