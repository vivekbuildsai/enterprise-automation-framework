"""External customer validation for the safe-extension + framework-native
scaffolding milestone: a sanitized, mature Python/pytest/Playwright
existing framework (API/DB/auth/validation/test-data/reporting, one
existing UI) receives a brand-new, zero-test UI that partially reuses the
existing backend. Runs the full pipeline — analyze -> discover -> correlate
-> extension plan -> scaffold — and verifies every safety guarantee this
milestone exists to provide.

Never executes anything from the sanitized fixture (`RepositoryAnalyzer`
is a static text scanner); the "new UI" is a local, controlled Playwright
target (`page.route`), never a real/remote application.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page

from framework.discovery.models import DiscoveryReport
from framework.discovery.ui_discovery import UIDiscoveryEngine
from framework.extension import paths as paths_module
from framework.extension.gap_analysis import build_extension_items, build_test_opportunities
from framework.extension.models import ExtensionClassification, ExtensionReport, ScaffoldTarget
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.extension.target import detect_scaffold_target
from framework.sync.analyzer import RepositoryAnalyzer

pytestmark = [pytest.mark.integration, pytest.mark.extension]

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_EXISTING_FRAMEWORK_ROOT = _FIXTURES / "scaffold_ready_framework"
_NEW_UI_PAGE_URL = "https://employee-portal.test/app/employee-details"


def _discover_new_employee_portal(page: Page):
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
            status=200, content_type="application/json", body='{"id": 42, "name": "Ada Lovelace"}'
        ),
    )
    page.route(
        "https://employee-portal.test/reports/custom-export",
        lambda route: route.fulfill(status=202, content_type="application/json", body="{}"),
    )
    return UIDiscoveryEngine(page).discover_page(_NEW_UI_PAGE_URL, capture_network=True)


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_full_pipeline_produces_a_python_pytest_playwright_scaffold_without_touching_anything(
    page: Page, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _snapshot(_EXISTING_FRAMEWORK_ROOT)
    before_modules = set(sys.modules)

    # 1. Analyze the existing framework — static, read-only.
    analysis = RepositoryAnalyzer().analyze(_EXISTING_FRAMEWORK_ROOT, source="scaffold-ready")
    assert detect_scaffold_target(analysis) == ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT

    # 2. Discover the new UI — local, controlled target only.
    new_ui_page = _discover_new_employee_portal(page)

    # 3. Correlate + extension plan.
    catalog = analysis.capability_catalog
    extension_report = ExtensionReport(
        existing_framework_source=analysis.source,
        new_ui_source="https://employee-portal.test",
        extension_items=build_extension_items([new_ui_page], catalog),
        test_opportunities=build_test_opportunities([new_ui_page], catalog),
    )
    by_subject = {item.subject: item for item in extension_report.extension_items}
    assert by_subject["GET /employees/42"].classification == ExtensionClassification.REUSE_EXISTING
    assert (
        by_subject["POST /reports/custom-export"].classification
        == ExtensionClassification.CREATE_NEW
    )

    # 4. Human review boundary: build the plan (no disk writes yet).
    discovery_report = DiscoveryReport(source="https://employee-portal.test", pages=[new_ui_page])
    files, manifest = build_scaffold_plan(analysis, discovery_report, extension_report)
    assert manifest.target == ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT
    assert "EmployeeApi.get_employee" in manifest.reused_capabilities

    # 5. Approve + write — only inside a project-root-safe output dir.
    monkeypatch.setattr(paths_module, "PROJECT_ROOT", tmp_path)
    output_dir = tmp_path / "generated" / "extension"
    written = write_scaffold_plan(files, output_dir)
    manifest_path = output_dir / "extension-manifest.json"
    manifest.save(manifest_path)

    # --- Safety guarantees ---------------------------------------------
    # Existing framework files are byte-for-byte unchanged.
    assert _snapshot(_EXISTING_FRAMEWORK_ROOT) == before
    # Never imported/executed the fixture's own source.
    assert not (set(sys.modules) - before_modules) & {"employee_api", "employee_repository"}
    # Nothing was ever written outside PROJECT_ROOT (tmp_path here).
    for path in written:
        assert path.is_relative_to(tmp_path)
    # No writes landed inside this repository's real site-packages/install path.
    assert not any("site-packages" in str(p) for p in written)

    # --- Generated content is framework-native and honest --------------
    page_object = next(p for p in written if p.name.endswith("_page.py"))
    test_file = next(p for p in written if p.name.startswith("test_"))
    page_content = page_object.read_text(encoding="utf-8")
    test_content = test_file.read_text(encoding="utf-8")

    assert "from framework.pages.base_page import BasePage" in page_content
    assert "GENERATED SCAFFOLD" in page_content
    assert "TODO: verify locator" in page_content  # the #notes input has no test_id/role/label

    assert "Reuses: EmployeeApi.get_employee (api/employee_api.py)" in test_content
    assert "class EmployeeApi" not in test_content
    assert "class ApiClient" not in test_content

    assert manifest_path.exists()
