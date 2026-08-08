"""Capability catalog extraction — the customer's existing framework as a
catalog of *named*, individually addressable reusable assets (API client
methods with endpoint patterns, DB repositories/tables, validators, Page
Objects/components, authentication mechanisms). Every capability here must
trace back to real source evidence; nothing is guessed beyond what a line
of source text actually shows (see framework/sync/capability_catalog.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync import RepositoryAnalyzer
from framework.sync.capability_catalog import build_capability_catalog
from framework.sync.models import CapabilityCategory

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def _catalog_for(root: Path) -> list:
    analysis = RepositoryAnalyzer().analyze(root, source=str(root))
    return analysis.capability_catalog.capabilities


def _by_category(capabilities: list, category: CapabilityCategory) -> list:
    return [c for c in capabilities if c.category == category]


@pytest.fixture
def employee_app(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "employee_api.py").write_text(
        "class EmployeeApi:\n"
        "    def get_employee(self, employee_id):\n"
        '        response = self._client.get(f"/employees/{employee_id}")\n'
        "        return response.json()\n"
        "\n"
        "    def search(self, name):\n"
        '        response = self._client.get("/employees/search")\n'
        "        return response.json()\n"
        "\n"
        "class EmployeeHelper:\n"
        "    def unrelated(self):\n"
        '        return self._client.get("/employees")\n'
    )
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "employee_repository.py").write_text(
        "class EmployeeRepository:\n"
        '    __tablename__ = "employee"\n'
        "\n"
        "    def find_audit_trail(self, employee_id):\n"
        '        query = "SELECT * FROM employee_audit WHERE id = ?"\n'
        "        return self.session.execute(query, [employee_id])\n"
    )
    (tmp_path / "validation").mkdir()
    (tmp_path / "validation" / "employee_validator.py").write_text(
        "class EmployeeValidator:\n"
        "    def validate(self, actual, expected):\n"
        "        return DataComparator.compare(actual, expected)\n"
    )
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "employee_page.py").write_text(
        "class EmployeePage:\n    def open(self):\n        pass\n"
    )
    (tmp_path / "pages" / "employee_card_component_page.py").write_text(
        "class EmployeeCard:\n    def render(self):\n        pass\n"
    )
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "readme.md").write_text("Authentication uses JWT for all API calls.\n")
    (tmp_path / "testdata").mkdir()
    (tmp_path / "testdata" / "employee_factory.py").write_text("class EmployeeFactory: pass\n")
    (tmp_path / "reporting.py").write_text("import allure\n")
    return tmp_path


def test_api_client_method_extracted_with_normalized_endpoint_and_verb(employee_app) -> None:
    api_clients = _by_category(_catalog_for(employee_app), CapabilityCategory.API_CLIENT)
    by_name = {c.name: c for c in api_clients}

    assert by_name["EmployeeApi.get_employee"].endpoint_pattern == "/employees/{param}"
    assert by_name["EmployeeApi.get_employee"].http_method == "GET"
    assert by_name["EmployeeApi.search"].endpoint_pattern == "/employees/search"
    assert by_name["EmployeeApi.search"].http_method == "GET"


def test_class_without_api_or_client_hint_is_never_treated_as_an_api_capability(
    employee_app,
) -> None:
    api_clients = _by_category(_catalog_for(employee_app), CapabilityCategory.API_CLIENT)

    assert not any(c.name.startswith("EmployeeHelper") for c in api_clients)


def test_trailing_slash_concatenation_path_normalizes_to_param() -> None:
    source = (
        "class OrderApi:\n"
        "    def get(self, order_id):\n"
        '        self._c.get("/orders/" + str(order_id))\n'
    )
    catalog = build_capability_catalog(
        Path("."),
        {Path("client.py"): source},
        authentication_mechanisms=[],
        page_object_hints=(),
    )
    api_clients = [c for c in catalog.capabilities if c.category == CapabilityCategory.API_CLIENT]

    assert api_clients[0].endpoint_pattern == "/orders/{param}"


def test_repository_class_and_table_references_extracted(employee_app) -> None:
    db_capabilities = _by_category(_catalog_for(employee_app), CapabilityCategory.DATABASE_UTILITY)
    names = {c.name for c in db_capabilities}

    assert "EmployeeRepository" in names
    assert "table:employee" in names
    assert "table:employee_audit" in names


def test_validator_class_and_data_comparator_usage_extracted(employee_app) -> None:
    validators = _by_category(_catalog_for(employee_app), CapabilityCategory.VALIDATION)
    names = {c.name for c in validators}

    assert "EmployeeValidator" in names
    assert "DataComparator" in names


def test_page_object_and_component_distinguished_by_filename(employee_app) -> None:
    capabilities = _catalog_for(employee_app)
    page_objects = _by_category(capabilities, CapabilityCategory.PAGE_OBJECT)
    components = _by_category(capabilities, CapabilityCategory.COMPONENT)

    assert {c.name for c in page_objects} == {"EmployeePage"}
    assert {c.name for c in components} == {"EmployeeCard"}


def test_authentication_mechanisms_are_reused_from_inventory_not_rederived(employee_app) -> None:
    auth_capabilities = _by_category(_catalog_for(employee_app), CapabilityCategory.AUTHENTICATION)

    assert {c.name for c in auth_capabilities} == {"JWT"}


def test_authentication_extraction_is_a_pure_passthrough() -> None:
    catalog = build_capability_catalog(
        Path("."),
        {},
        authentication_mechanisms=["OAuth", "API Key"],
        page_object_hints=(),
    )
    auth_capabilities = [
        c for c in catalog.capabilities if c.category == CapabilityCategory.AUTHENTICATION
    ]

    assert {c.name for c in auth_capabilities} == {"OAuth", "API Key"}
    assert all(c.source_file == "" for c in auth_capabilities)


def test_test_data_and_reporting_assets_are_catalogued_with_source_evidence(employee_app) -> None:
    capabilities = _catalog_for(employee_app)
    test_data = _by_category(capabilities, CapabilityCategory.TEST_DATA)
    reporting = _by_category(capabilities, CapabilityCategory.REPORTING)

    assert any(c.source_file == "testdata/employee_factory.py" for c in test_data)
    assert any(c.name == "Allure" and c.source_file == "reporting.py" for c in reporting)


def test_robot_requests_library_get_on_session_extracted_as_api_client() -> None:
    api_clients = _by_category(
        _catalog_for(_FIXTURES / "robot_requests_library"), CapabilityCategory.API_CLIENT
    )

    assert len(api_clients) == 1
    assert api_clients[0].http_method == "GET"
    assert api_clients[0].endpoint_pattern == "/users"


def test_mixed_language_fixture_extracts_python_api_helper() -> None:
    api_clients = _by_category(
        _catalog_for(_FIXTURES / "mixed_language"), CapabilityCategory.API_CLIENT
    )

    assert any(c.name == "ApiTestUtils.get_user" for c in api_clients)


def test_repository_with_no_matching_evidence_yields_empty_catalog_not_an_error(
    tmp_path,
) -> None:
    (tmp_path / "README.md").write_text("Nothing relevant here.\n")

    assert _catalog_for(tmp_path) == []
