import allure
import pytest

from framework.pages.administration import AdministrationPage, AdministrationTestDataBuilder

pytestmark = pytest.mark.skip(
    reason="Administration is a skeleton module — no real target application environment "
    "is reachable to run this against. Structure is real; remove this skip once real "
    "selectors + a target environment exist."
)


@allure.feature("Administration")
@pytest.mark.ui
@pytest.mark.e2e
class TestRoleCreation:
    def test_create_role(self, page, settings) -> None:
        role = AdministrationTestDataBuilder.random_role()
        admin_page = AdministrationPage(page)
        admin_page.base_url = str(settings.ui.base_url)
        admin_page.open()

        with allure.step(f"Create role '{role.name}'"):
            admin_page.create_role(role.name)
