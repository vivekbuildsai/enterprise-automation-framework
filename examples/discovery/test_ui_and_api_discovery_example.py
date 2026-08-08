"""Example D — Application Discovery.

Demonstrates:

    sample application (a local HTML page)
          |
    UIDiscoveryEngine       (real element discovery + locator metadata)
          |
    discover_from_openapi   (real API/network metadata, from a small sample spec)
          |
    DiscoveryReport          (the normalized, saved artifact)

Entirely local — no live application required.

Run:
    poetry run pytest examples/discovery -v
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page

from framework.discovery import DiscoveryReport, UIDiscoveryEngine, discover_from_openapi

_SAMPLE_PAGE_HTML = """
<html><body>
  <button data-testid="submit-login">Sign In</button>
  <label for="username">Username</label>
  <input id="username" name="username" type="text" />
  <a href="/reports" aria-label="Open reports">Reports</a>
</body></html>
"""

_SAMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "paths": {
        "/users": {
            "get": {
                "summary": "List users",
                "responses": {
                    "200": {"content": {"application/json": {"schema": {"type": "array"}}}}
                },
            }
        },
        "/users/{id}": {
            "get": {"summary": "Get a single user"},
        },
    },
}


@allure.feature("Example: Application Discovery")
@allure.story("Discover UI locators and API endpoints, save a DiscoveryReport")
def test_discover_ui_and_api_metadata(page: Page, tmp_path) -> None:
    with allure.step("Discover UI elements from a sample local page"):
        page.set_content(_SAMPLE_PAGE_HTML)
        discovered_page = UIDiscoveryEngine(page).discover_page()

    with allure.step("Verify locator metadata uses the real priority ladder"):
        by_strategy = {el.locator.strategy: el for el in discovered_page.elements}
        assert by_strategy["test_id"].locator.value == "submit-login"
        assert by_strategy["label"].locator.value == "Username"
        assert by_strategy["role"].locator.accessible_name == "Open reports"

    with allure.step("Discover API endpoints from a sample OpenAPI spec"):
        endpoints = discover_from_openapi(_SAMPLE_OPENAPI_SPEC)
        assert {(e.method, e.path) for e in endpoints} == {
            ("GET", "/users"),
            ("GET", "/users/{id}"),
        }

    with allure.step("Save the combined, normalized DiscoveryReport"):
        report = DiscoveryReport(source="example", pages=[discovered_page], endpoints=endpoints)
        report_path = tmp_path / "discovery_report.json"
        report.save(report_path)

        reloaded = DiscoveryReport.load(report_path)
        assert len(reloaded.pages[0].elements) == 3
        assert len(reloaded.endpoints) == 2
