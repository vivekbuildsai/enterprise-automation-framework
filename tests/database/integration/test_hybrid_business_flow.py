from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page
from sqlalchemy.engine import Connection

from framework.api.services import ApiValidator
from framework.config import EnvironmentSettings
from framework.database.models import Subscriber
from framework.database.repositories import SubscriberRepository
from framework.database.validators import SubscriberValidator
from framework.hybrid import ValidationFacade
from framework.pages import LoginPage

pytestmark = [pytest.mark.integration, pytest.mark.hybrid, pytest.mark.database]


@allure.feature("Hybrid Validation")
@allure.story("Business-flow shape from the Milestone brief")
class TestHybridBusinessFlow:
    """Reproduces the exact shape the milestone brief specifies::

        login_page.login(user)
        dashboard.verify_dashboard()
        api_validator.verify_dashboard(user)
        database_validator.verify_dashboard(user)

    against three real backends (the-internet.herokuapp.com for UI,
    dummyjson.com for API, SQLite for DB — see docs/DatabaseConfiguration.md
    for pointing the DB leg at PostgreSQL/MySQL/Oracle/SQL Server instead).
    `validation_facade` is built from `settings.validation_mode`
    (`config/environments/dev.yaml`, currently `ui_api_database`) — this
    test body is unchanged no matter what that config value is; only which
    of `verify_api`/`verify_database` actually execute changes.
    """

    def test_login_verified_across_ui_api_and_database(
        self,
        page: Page,
        settings: EnvironmentSettings,
        api_validator: ApiValidator,
        subscriber_repository: SubscriberRepository,
        db_schema: None,
        db_connection: Connection,
        validation_facade: ValidationFacade,
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)

        with allure.step("UI: log in and reach the secure area"):
            login_page.open()
            dashboard = login_page.login(settings.ui.login_username, settings.ui.login_password)
            assert dashboard.is_loaded()

        with allure.step(
            "API: cross-check credentials against a real backend (runs iff mode includes API)"
        ):
            validation_facade.verify_api(lambda: api_validator.verify_login("emilys", "emilyspass"))

        with allure.step(
            "Database: cross-check a persisted record (runs iff mode includes database)"
        ):
            validation_facade.verify_database(
                lambda: self._verify_subscriber_in_database(subscriber_repository, db_connection)
            )

    @staticmethod
    def _verify_subscriber_in_database(
        subscriber_repository: SubscriberRepository, db_connection: Connection
    ) -> None:
        subscriber_repository.create(
            Subscriber(
                subscriber_id="HYBRID-1",
                msisdn="447700900123",
                imsi="234000000000001",
                status="ACTIVE",
                cos="Gold",
                tenant_id="T-HYBRID",
                network_id="N-HYBRID",
                created_at="2026-08-04T00:00:00",
                updated_at="2026-08-04T00:00:00",
            )
        )
        db_connection.commit()
        SubscriberValidator(subscriber_repository).verify_against_database(
            "HYBRID-1", {"status": "ACTIVE", "cos": "Gold"}, fields=["status", "cos"]
        ).raise_if_mismatched()
