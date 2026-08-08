from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page

from framework.models.dashboard_config import WidgetExtractors, WidgetIdentify
from framework.network import JsonRpcInterceptor, NetworkInterceptor, WidgetDataExtractor

pytestmark = pytest.mark.smoke

_RPC_RESPONSE = {
    "rows": [
        {"country": "US", "total": 100},
        {"country": "DE", "total": 42},
    ]
}


def _mock_dashboard_endpoint(page: Page) -> None:
    def handle_route(route: object) -> None:
        route.fulfill(  # type: ignore[attr-defined]
            status=200,
            content_type="application/json",
            body=json.dumps(_RPC_RESPONSE),
        )

    page.route("https://example.test/api/dashboard", handle_route)


def _fire_jsonrpc_request(page: Page) -> None:
    page.evaluate(
        """
        () => fetch('https://example.test/api/dashboard', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({method: 'widget.top_countries', params: {}, id: 1}),
        })
        """
    )


def test_network_interceptor_captures_matching_response(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    _mock_dashboard_endpoint(page)

    with NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
        _fire_jsonrpc_request(page)
        page.wait_for_timeout(50)

    assert len(interceptor.captured) == 1
    exchange = interceptor.captured[0]
    assert exchange.status == 200
    assert exchange.response_json == _RPC_RESPONSE


def test_jsonrpc_interceptor_filters_by_method_name(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    _mock_dashboard_endpoint(page)

    with JsonRpcInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
        _fire_jsonrpc_request(page)
        page.wait_for_timeout(50)

    matches = interceptor.calls_named("widget.top_countries")
    assert len(matches) == 1
    assert interceptor.calls_named("does.not.exist") == []


def test_widget_data_extractor_finds_and_extracts_rows(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    _mock_dashboard_endpoint(page)

    with NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
        _fire_jsonrpc_request(page)
        page.wait_for_timeout(50)

    identify = WidgetIdentify(must_have=["top_countries"], must_not_have=["forecast"])
    match = WidgetDataExtractor.find_matching(identify, interceptor.captured)
    assert match is not None

    extractors = WidgetExtractors(dimension="country", metric="total")
    rows = WidgetDataExtractor.extract_rows(match, extractors)

    assert rows == [
        {"dimension": "US", "total": 100},
        {"dimension": "DE", "total": 42},
    ]


def test_widget_data_extractor_returns_none_when_no_exchange_matches(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    _mock_dashboard_endpoint(page)

    with NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
        _fire_jsonrpc_request(page)
        page.wait_for_timeout(50)

    identify = WidgetIdentify(must_have=["not-in-any-captured-request"])
    assert WidgetDataExtractor.find_matching(identify, interceptor.captured) is None


def test_widget_data_extractor_honors_skip_if_request_contains(page: Page) -> None:
    page.set_content("<html><body></body></html>")
    _mock_dashboard_endpoint(page)

    with NetworkInterceptor(page, url_pattern="**/api/dashboard") as interceptor:
        _fire_jsonrpc_request(page)
        page.wait_for_timeout(50)

    identify = WidgetIdentify(must_have=["top_countries"], skip_if_request_contains="top_countries")
    assert WidgetDataExtractor.find_matching(identify, interceptor.captured) is None
