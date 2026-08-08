from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from framework.api.client import ApiClient
from framework.database.repositories import SubscriberRepository
from framework.database.validators import SubscriberValidator
from framework.enums import ValidationMode
from framework.hybrid import ValidationFacade
from framework.pages import LoginPage
from framework.testdata.builders import UserBuilder
from framework.testdata.seed import ApiSeeder

pytestmark = [
    pytest.mark.testdata,
    pytest.mark.database,
    pytest.mark.integration,
    pytest.mark.hybrid,
]


@allure.feature("Test Data Management")
@allure.story("TDM data flows through UI -> API -> DB -> cleanup without changing test logic")
@pytest.mark.parametrize("mode", list(ValidationMode))
def test_tdm_scenario_flows_through_every_layer_by_config_only(
    mode: ValidationMode,
    page: Page,
    base_url: str,
    api_client: ApiClient,
    seeded_scenario,
    subscriber_repository: SubscriberRepository,
    db_schema,
) -> None:
    """The exact flow the milestone brief specifies:

        UI test -> consume test data -> API validation -> DB validation -> cleanup

    All test data comes from the TDM layer (`UserBuilder`, `seeded_scenario`
    -> `ScenarioLibrary`) — nothing here is a hardcoded business value. The
    test body is identical for all four `ValidationMode` values; only
    `facade.verify_api`/`verify_database` actually executing changes.
    Cleanup is automatic via `seeded_scenario`'s `cleanup_registry`
    integration (see framework/testdata/fixtures/testdata_fixtures.py) —
    this test never calls a delete method itself.
    """
    facade = ValidationFacade(mode)

    # 1. TDM produces the data — a user profile for the API leg, a whole
    #    scenario (tenant/network/subscriber/zone) for the DB leg.
    user = UserBuilder().build()
    handle = seeded_scenario("new_subscriber")
    subscriber = next(e for e in handle.database_entities if type(e).__name__ == "Subscriber")

    executed: list[str] = []

    # 2. UI: drives a real page — the milestone's demo UI target only
    #    accepts its own fixed demo credentials, so the TDM-built `user`
    #    isn't literally logged in here; it's threaded through unchanged
    #    to the API leg below instead, which is where it's actually usable.
    def ui_check() -> None:
        login_page = LoginPage(page)
        login_page.base_url = base_url
        login_page.open()
        dashboard = login_page.login("tomsmith", "SuperSecretPassword!")
        assert dashboard.is_loaded()
        executed.append("ui")

    # 3. API: creates the TDM-built user via a real API call and confirms it round-trips.
    def api_check() -> None:
        seeder = ApiSeeder(api_client, "/users/add")
        created = seeder.seed_one(user.to_api_create_request())
        assert created["firstName"] == user.first_name
        executed.append("api")

    # 4. Database: confirms the TDM-seeded subscriber is actually there.
    def database_check() -> None:
        SubscriberValidator(subscriber_repository).verify_against_database(
            subscriber.subscriber_id,
            {"status": subscriber.status, "cos": subscriber.cos},
            fields=["status", "cos"],
        ).raise_if_mismatched()
        executed.append("database")

    with allure.step(f"Run TDM -> UI/API/DB flow under validation_mode={mode.value}"):
        facade.run(ui=ui_check, api=api_check, database=database_check)

    expected = ["ui"]
    if facade.api_enabled:
        expected.append("api")
    if facade.database_enabled:
        expected.append("database")
    assert executed == expected
    # 5. Cleanup: nothing explicit here — `seeded_scenario`'s cleanup_registry
    #    integration deletes `subscriber` (and its tenant/network) after
    #    this test, regardless of pass/fail.
