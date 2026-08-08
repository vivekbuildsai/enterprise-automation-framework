from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from framework.api.client import ApiClient
from framework.database.models import Tenant
from framework.database.repositories import TenantRepository
from framework.enums import ValidationMode
from framework.hybrid import ValidationFacade

pytestmark = [pytest.mark.integration, pytest.mark.hybrid, pytest.mark.database]


@allure.feature("Hybrid Validation")
@allure.story("ValidationFacade dispatches per mode, with no test-code changes")
@pytest.mark.parametrize("mode", list(ValidationMode))
def test_validation_facade_runs_only_the_layers_its_mode_selects(
    mode: ValidationMode,
    page: Page,
    base_url: str,
    api_client: ApiClient,
    db_schema: None,
    db_connection,
    tenant_repository: TenantRepository,
) -> None:
    """One test body, four modes — proves UI / UI+API / UI+DB / UI+API+DB
    are all reachable through identical code, exercised against three real
    backends: a real Playwright page load (the-internet.herokuapp.com), a
    real API call (dummyjson.com), and a real SQLite write. Only `mode`
    (the in-test stand-in for `validation_mode` in
    `config/environments/<env>.yaml`) changes between parametrize cases.
    """
    facade = ValidationFacade(mode)
    executed: list[str] = []

    def ui_check() -> None:
        page.goto(base_url)
        assert page.title() != ""
        executed.append("ui")

    def api_check() -> None:
        response = api_client.get("/products/1")
        assert response.status_code == 200
        executed.append("api")

    def database_check() -> None:
        tenant_id = f"T-{mode.value}"
        tenant_repository.create(
            Tenant(
                tenant_id=tenant_id,
                tenant_code="X",
                tenant_name="X",
                status="ACTIVE",
                created_at="t",
            )
        )
        db_connection.commit()
        assert tenant_repository.get_by_id(tenant_id).status == "ACTIVE"
        executed.append("database")

    with allure.step(f"Run facade.run() under validation_mode={mode.value}"):
        facade.run(ui=ui_check, api=api_check, database=database_check)

    expected = ["ui"]
    if facade.api_enabled:
        expected.append("api")
    if facade.database_enabled:
        expected.append("database")

    assert executed == expected
