"""RAW -> NORMALIZE -> DEDUPLICATE -> CLASSIFY pipeline — the fix for the
validated bug where CSS/JS/image/jquery/bootstrap/combo/barebone.jsp
requests and a login-page redirect were treated as application-capability
evidence. Every summary-count assertion here traces back to a real
`len()`, matching the "no invented counts" requirement the module docstring
states.
"""

from __future__ import annotations

import pytest

from framework.discovery.models import DiscoveredNetworkCall
from framework.extension.models import NetworkCallClassification
from framework.extension.network_classification import classify_network_calls, page_host_from_url

pytestmark = pytest.mark.extension


def _call(**overrides: object) -> DiscoveredNetworkCall:
    defaults: dict[str, object] = {
        "method": "GET",
        "path": "/",
        "status": 200,
        "host": "app.example.com",
    }
    defaults.update(overrides)
    return DiscoveredNetworkCall(**defaults)  # type: ignore[arg-type]


def test_login_path_is_classified_authentication_not_application_api() -> None:
    call = _call(path="/c/portal/login")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.AUTHENTICATION
    assert result.summary.authentication_count == 1
    assert result.summary.application_candidate_count == 0


@pytest.mark.parametrize(
    "path",
    [
        "/html/js/jquery.min.js",
        "/html/themes/classic/css/bootstrap.min.css",
        "/js/barebone.jsp",
    ],
)
def test_known_framework_asset_paths_are_not_application_api(path: str) -> None:
    call = _call(path=path)

    result = classify_network_calls([call], page_host="app.example.com")

    classification = result.classified_calls[0].classification
    assert classification in (
        NetworkCallClassification.FRAMEWORK_ASSET,
        NetworkCallClassification.STATIC_ASSET,
    )
    assert result.summary.application_candidate_count == 0


def test_static_extension_is_static_asset() -> None:
    call = _call(path="/images/logo.png")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.STATIC_ASSET
    assert result.summary.static_or_framework_ignored == 1


def test_combo_path_is_static_asset() -> None:
    call = _call(path="/combo/", query_param_names=["b", "t"])

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.STATIC_ASSET


def test_document_extension_is_document() -> None:
    call = _call(path="/reports/invoice.pdf")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.DOCUMENT
    assert result.summary.document_ignored == 1


def test_known_analytics_host_is_analytics() -> None:
    call = _call(path="/collect", host="www.google-analytics.com")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.ANALYTICS
    assert result.summary.analytics_ignored == 1


def test_different_host_with_no_analytics_match_is_third_party() -> None:
    call = _call(path="/widget", host="cdn.unrelated-vendor.com")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.THIRD_PARTY
    assert result.summary.third_party_ignored == 1


def test_same_origin_json_api_call_is_application_api() -> None:
    call = _call(
        method="POST",
        path="/api/employees/search",
        host="app.example.com",
        request_body_keys=["query"],
        response_body_keys=["results"],
    )

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.APPLICATION_API
    assert result.summary.application_candidate_count == 1


def test_same_origin_extensionless_path_with_no_body_is_still_application_api() -> None:
    call = _call(path="/api/employees/42", host="app.example.com")

    result = classify_network_calls([call], page_host="app.example.com")

    assert result.classified_calls[0].classification is NetworkCallClassification.APPLICATION_API


def test_no_page_host_never_crashes_and_still_classifies() -> None:
    call = _call(path="/api/employees/42", host="app.example.com")

    result = classify_network_calls([call], page_host="")

    assert result.classified_calls[0].classification is not None


def test_duplicate_calls_collapse_to_one_with_correct_duplicate_count() -> None:
    calls = [
        _call(path="/combo/", query_param_names=["b", "t"]),
        _call(path="/combo/", query_param_names=["b", "t"]),
        _call(path="/combo/", query_param_names=["b", "t"]),
    ]

    result = classify_network_calls(calls, page_host="app.example.com")

    assert len(result.classified_calls) == 1
    assert result.classified_calls[0].duplicate_count == 3
    assert result.summary.raw_count == 3
    assert result.summary.duplicates_removed == 2
    assert len(result.raw_calls) == 3


def test_query_param_names_differing_are_not_deduplicated_together() -> None:
    calls = [
        _call(path="/api/search", query_param_names=["q"]),
        _call(path="/api/search", query_param_names=["q", "page"]),
    ]

    result = classify_network_calls(calls, page_host="app.example.com")

    assert len(result.classified_calls) == 2
    assert result.summary.duplicates_removed == 0


def test_application_and_auth_calls_excludes_noise() -> None:
    calls = [
        _call(path="/c/portal/login"),
        _call(path="/html/js/jquery.min.js"),
        _call(path="/images/logo.png"),
        _call(path="/collect", host="www.google-analytics.com"),
        _call(path="/api/employees/42", request_body_keys=["id"]),
    ]

    result = classify_network_calls(calls, page_host="app.example.com")

    kept = result.application_and_auth_calls()
    assert len(kept) == 2
    assert {c.path for c in kept} == {"/c/portal/login", "/api/employees/42"}


def test_realistic_page_mostly_noise_yields_a_small_application_surface() -> None:
    """Mirrors the validated real-world bug: dozens of raw network calls on
    one page, the overwhelming majority of which are static/framework/
    analytics noise, not application API traffic.
    """
    calls = [_call(path=f"/html/js/lib-{i}.js") for i in range(40)]
    calls += [_call(path=f"/images/icon-{i}.png") for i in range(30)]
    calls += [_call(path="/collect", host="www.google-analytics.com") for _ in range(5)]
    calls += [_call(path="/c/portal/login")]
    calls += [
        _call(path="/api/employees/search", request_body_keys=["query"]),
        _call(path="/api/employees/42"),
        _call(path="/api/departments"),
        _call(path="/api/reports/summary", response_body_keys=["total"]),
        _call(path="/api/session/refresh"),
    ]

    result = classify_network_calls(calls, page_host="app.example.com")

    assert result.summary.raw_count == 81
    assert result.summary.application_candidate_count == 5
    assert result.summary.authentication_count == 1
    assert len(result.application_and_auth_calls()) == 6


def test_page_host_from_url_extracts_bare_hostname() -> None:
    assert (
        page_host_from_url("https://app.example.com:8443/dashboard?x=1") == "app.example.com:8443"
    )
