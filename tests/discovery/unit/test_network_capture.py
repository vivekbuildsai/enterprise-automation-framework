"""Opt-in network-call capture on `UIDiscoveryEngine.discover_page` — the
new-UI discovery half of the "existing API reuse" capability. Every
captured exchange must be shape-only (method/path/status/key names): never
a raw header, query value, or body value, so a discovery report stays safe
to persist even against an authenticated session (see
`framework.discovery.models.DiscoveredNetworkCall`,
`framework.discovery.ui_discovery._json_shape`).
"""

from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page

from framework.discovery import UIDiscoveryEngine
from framework.discovery.ui_discovery import _json_shape

pytestmark = pytest.mark.discovery


def test_json_shape_collects_dotted_key_paths_never_values() -> None:
    shape = _json_shape({"id": 42, "manager": {"id": 7, "name": "Ada"}, "tags": ["a", "b"]})

    assert set(shape) == {"id", "manager", "manager.id", "manager.name", "tags"}
    assert "42" not in shape
    assert "Ada" not in shape


def test_json_shape_walks_a_list_via_its_first_element_only() -> None:
    shape = _json_shape([{"id": 1, "name": "first"}, {"id": 2, "name": "second"}])

    assert set(shape) == {"id", "name"}


def test_json_shape_of_a_scalar_or_none_is_empty() -> None:
    assert _json_shape(42) == []
    assert _json_shape("just a string") == []
    assert _json_shape(None) == []
    assert _json_shape([]) == []


def test_discover_page_default_never_attaches_a_network_listener(page: Page) -> None:
    """`capture_network` defaults to `False` — existing DOM-only callers
    must see zero behavior change, so no network calls are ever recorded
    unless explicitly opted in.
    """
    page.set_content("<html><body><button>Click</button></body></html>")

    result = UIDiscoveryEngine(page).discover_page()

    assert result.network_calls == []


def test_discover_page_captures_get_call_shape_only(page: Page) -> None:
    page.route(
        "https://example.test/employees",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body=(
                "<html><body><script>"
                "fetch('/api/employees/42?verbose=true');"
                "</script></body></html>"
            ),
        ),
    )
    page.route(
        "https://example.test/api/employees/**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"id": 42, "name": "Ada", "manager": {"id": 7}}),
        ),
    )

    result = UIDiscoveryEngine(page).discover_page(
        "https://example.test/employees", capture_network=True
    )

    call = next(c for c in result.network_calls if c.path == "/api/employees/42")
    assert call.method == "GET"
    assert call.status == 200
    assert call.query_param_names == ["verbose"]
    assert set(call.response_body_keys) == {"id", "name", "manager", "manager.id"}
    # Never the raw value that flowed through the exchange.
    assert not any("Ada" in field for field in call.response_body_keys)
    assert not any("true" in field for field in call.query_param_names)


def test_discover_page_captures_post_request_body_shape_only(page: Page) -> None:
    page.route(
        "https://example.test/new-employee",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body=(
                "<html><body><script>"
                "fetch('/api/employees', {"
                "  method: 'POST',"
                "  headers: {'Content-Type': 'application/json'},"
                "  body: JSON.stringify({name: 'Ada', address: {city: 'Metropolis'}})"
                "});"
                "</script></body></html>"
            ),
        ),
    )
    page.route(
        "https://example.test/api/employees",
        lambda route: route.fulfill(status=201, content_type="application/json", body="{}"),
    )

    result = UIDiscoveryEngine(page).discover_page(
        "https://example.test/new-employee", capture_network=True
    )

    call = next(c for c in result.network_calls if c.path == "/api/employees")
    assert call.method == "POST"
    assert call.status == 201
    assert set(call.request_body_keys) == {"name", "address", "address.city"}
    assert not any("Metropolis" in field for field in call.request_body_keys)


def test_crawl_threads_capture_network_through_to_each_page(page: Page) -> None:
    page.route(
        "https://example.test/start",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="<script>fetch('/api/ping');</script>",
        ),
    )
    page.route(
        "https://example.test/api/ping",
        lambda route: route.fulfill(status=200, content_type="application/json", body="{}"),
    )

    pages = UIDiscoveryEngine(page).crawl(
        "https://example.test/start", max_pages=1, capture_network=True
    )

    assert any(c.path == "/api/ping" for c in pages[0].network_calls)
