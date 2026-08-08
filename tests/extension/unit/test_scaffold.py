"""Framework-native scaffold generation — the "write actual draft source
files, but only for CREATE_NEW/EXTEND_EXISTING, only in the customer's own
detected style, only under a project-root-safe output directory" core of
this milestone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.discovery.models import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredNetworkCall,
    DiscoveredPage,
    DiscoveryReport,
)
from framework.exceptions import ConfigurationError
from framework.extension import paths as paths_module
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
    ScaffoldFileKind,
    ScaffoldTarget,
    TestOpportunity,
)
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.sync.models import CapabilityCategory, ExistingCapability, RepositoryAnalysis

pytestmark = pytest.mark.extension


@pytest.fixture(autouse=True)
def _project_root_is_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`write_scaffold_plan` refuses to write outside
    `framework.project_root.PROJECT_ROOT` — every test in this file treats
    `tmp_path` as the customer's project root so writes to `tmp_path` (or
    any subdirectory of it) pass containment.
    """
    monkeypatch.setattr(paths_module, "PROJECT_ROOT", tmp_path)


def _employee_page() -> DiscoveredPage:
    return DiscoveredPage(
        url="https://example.test/employees/42",
        title="Employee Details",
        elements=[
            DiscoveredElement(
                tag="button",
                element_type="button",
                text="Export",
                locator=DiscoveredLocator(strategy="test_id", value="export-btn"),
            ),
            DiscoveredElement(
                tag="input",
                element_type="textbox",
                locator=DiscoveredLocator(strategy="css", value="#notes"),
            ),
        ],
        network_calls=[DiscoveredNetworkCall(method="GET", path="/employees/42", status=200)],
    )


def _employee_capability() -> ExistingCapability:
    return ExistingCapability(
        category=CapabilityCategory.API_CLIENT,
        name="EmployeeApi.get_employee",
        source_file="api/employee_api.py",
        endpoint_pattern="/employees/{param}",
        http_method="GET",
    )


def _extension_report() -> ExtensionReport:
    return ExtensionReport(
        extension_items=[
            ExtensionItem(
                subject="Employee Details",
                subject_type=ExtensionSubjectType.UI_PAGE,
                classification=ExtensionClassification.CREATE_NEW,
                reason="new page",
            ),
            ExtensionItem(
                subject="GET /employees/42",
                subject_type=ExtensionSubjectType.API_ENDPOINT,
                classification=ExtensionClassification.REUSE_EXISTING,
                matched_capability=_employee_capability(),
                reason="matches",
            ),
            ExtensionItem(
                subject="Authentication",
                subject_type=ExtensionSubjectType.AUTHENTICATION,
                classification=ExtensionClassification.MANUAL_REVIEW,
                reason="ambiguous",
            ),
        ],
        test_opportunities=[
            TestOpportunity(
                name="Employee Details",
                page_url="https://example.test/employees/42",
                suggested_scenario_types=["happy_path", "validation"],
            )
        ],
    )


def _discovery_report() -> DiscoveryReport:
    return DiscoveryReport(source="new-ui", pages=[_employee_page()])


def _analysis() -> RepositoryAnalysis:
    return RepositoryAnalysis(source="existing-repo")


@pytest.mark.parametrize(
    ("target", "page_relative", "test_relative"),
    [
        (
            ScaffoldTarget.JAVA_SELENIUM_TESTNG,
            "pages/EmployeeDetailsPage.java",
            "tests/EmployeeDetailsTest.java",
        ),
        (
            ScaffoldTarget.JAVA_SELENIUM_JUNIT,
            "pages/EmployeeDetailsPage.java",
            "tests/EmployeeDetailsTest.java",
        ),
        (
            ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
            "pages/employee_details_page.py",
            "tests/test_employee_details.py",
        ),
        (
            ScaffoldTarget.TYPESCRIPT_PLAYWRIGHT,
            "pages/employee_details_page.ts",
            "tests/employee_details.spec.ts",
        ),
        (
            ScaffoldTarget.ROBOT_FRAMEWORK,
            "resources/employee_details.resource",
            "tests/employee_details.robot",
        ),
    ],
)
def test_each_supported_target_generates_the_expected_files(
    target: ScaffoldTarget, page_relative: str, test_relative: str
) -> None:
    files, manifest = build_scaffold_plan(
        _analysis(), _discovery_report(), _extension_report(), target=target
    )

    relative_paths = {f.relative_path for f in files}
    assert page_relative in relative_paths
    assert test_relative in relative_paths
    assert "README.md" in relative_paths
    assert manifest.target == target
    assert manifest.files == [f.relative_path for f in files]


def test_unknown_target_generates_only_a_readme_no_fabricated_code() -> None:
    files, manifest = build_scaffold_plan(
        _analysis(), _discovery_report(), _extension_report(), target=ScaffoldTarget.UNKNOWN
    )

    assert [f.relative_path for f in files] == ["README.md"]
    assert manifest.target == ScaffoldTarget.UNKNOWN
    assert not manifest.newly_generated_capabilities


def test_generated_page_object_carries_the_scaffold_notice_and_todo_markers() -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    page_file = next(f for f in files if f.kind == ScaffoldFileKind.PAGE_OBJECT)

    assert "GENERATED SCAFFOLD" in page_file.content
    assert "REVIEW REQUIRED" in page_file.content
    assert "production ready" not in page_file.content.lower() or "not production ready" in (
        page_file.content.lower()
    )
    # The css-locator input has no test_id/role/label — must be flagged.
    assert "TODO: verify locator" in page_file.content


def test_confirmed_locator_does_not_get_a_todo() -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    page_file = next(f for f in files if f.kind == ScaffoldFileKind.PAGE_OBJECT)

    # The test_id-locator element is high-confidence evidence.
    assert "confirmed locator (test_id)" in page_file.content


def test_generated_test_references_the_existing_capability_never_a_new_client() -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    test_file = next(f for f in files if f.kind == ScaffoldFileKind.TEST)

    assert "Reuses: EmployeeApi.get_employee (api/employee_api.py)" in test_file.content
    assert "class ApiClient" not in test_file.content
    assert "class EmployeeApi" not in test_file.content


def test_test_file_has_one_scenario_per_suggested_scenario_type() -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    test_file = next(f for f in files if f.kind == ScaffoldFileKind.TEST)

    assert "test_employee_details_happy_path" in test_file.content
    assert "test_employee_details_validation" in test_file.content


def test_manifest_records_reused_and_manual_review_items() -> None:
    _, manifest = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )

    assert "EmployeeApi.get_employee" in manifest.reused_capabilities
    assert "Authentication" in manifest.manual_review_items
    assert "Employee Details" in manifest.newly_generated_capabilities


def test_manifest_never_claims_production_ready() -> None:
    _, manifest = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    assert (
        "production ready" not in manifest.confidence.lower()
        or "not" in manifest.confidence.lower()
    )
    assert "review required" in manifest.confidence.lower()


def test_only_create_new_and_extend_existing_pages_are_scaffolded() -> None:
    """A REUSE_EXISTING page must never be scaffolded — there's nothing
    new to generate for it.
    """
    report = _extension_report()
    report.extension_items[0] = ExtensionItem(
        subject="Employee Details",
        subject_type=ExtensionSubjectType.UI_PAGE,
        classification=ExtensionClassification.REUSE_EXISTING,
        matched_capability=ExistingCapability(
            category=CapabilityCategory.PAGE_OBJECT,
            name="EmployeeDetailsPage",
            source_file="pages/employee_details_page.py",
        ),
        reason="already automated",
    )

    files, manifest = build_scaffold_plan(
        _analysis(), _discovery_report(), report, target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT
    )

    assert [f.relative_path for f in files] == ["README.md"]
    assert manifest.newly_generated_capabilities == []


# --- write_scaffold_plan ----------------------------------------------------


def test_write_scaffold_plan_writes_every_file(tmp_path: Path) -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )

    written = write_scaffold_plan(files, tmp_path)

    assert len(written) == len(files)
    for path in written:
        assert path.exists()
        assert path.is_relative_to(tmp_path)


def test_write_scaffold_plan_dry_run_writes_nothing(tmp_path: Path) -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )

    planned = write_scaffold_plan(files, tmp_path, dry_run=True)

    assert len(planned) == len(files)
    assert not any(p.exists() for p in planned)


def test_write_scaffold_plan_refuses_to_overwrite_by_default(tmp_path: Path) -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    write_scaffold_plan(files, tmp_path)

    with pytest.raises(ConfigurationError, match="Refusing to overwrite"):
        write_scaffold_plan(files, tmp_path)


def test_write_scaffold_plan_overwrite_protection_is_all_or_nothing(tmp_path: Path) -> None:
    """One pre-existing conflicting file must block the *entire* write —
    never a partial write that silently clobbers some customer files but
    not others.
    """
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    conflicting = next(f for f in files if f.relative_path == "README.md")
    target_path = tmp_path / conflicting.relative_path
    target_path.write_text("pre-existing customer content", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Refusing to overwrite"):
        write_scaffold_plan(files, tmp_path)

    other_file = next(f for f in files if f.relative_path != "README.md")
    assert not (tmp_path / other_file.relative_path).exists()
    assert target_path.read_text(encoding="utf-8") == "pre-existing customer content"


def test_write_scaffold_plan_overwrite_flag_allows_it(tmp_path: Path) -> None:
    files, _ = build_scaffold_plan(
        _analysis(),
        _discovery_report(),
        _extension_report(),
        target=ScaffoldTarget.PYTHON_PYTEST_PLAYWRIGHT,
    )
    write_scaffold_plan(files, tmp_path)

    written = write_scaffold_plan(files, tmp_path, overwrite=True)
    assert len(written) == len(files)
