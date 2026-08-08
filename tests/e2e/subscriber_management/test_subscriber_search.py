import allure
import pytest

from framework.config import EnvironmentSettings
from framework.pages.subscriber_management import SubscriberAssertions, SubscriberManagementPage
from framework.utilities import TestDataLoader
from framework.workflows.subscriber_search_workflow import SubscriberSearchWorkflow


@allure.feature("Subscriber Management")
@pytest.mark.ui
@pytest.mark.e2e
class TestSubscriberSearch:
    def test_search_existing_subscriber_returns_matching_row(
        self, page, settings: EnvironmentSettings
    ) -> None:
        test_data = TestDataLoader.load_json("subscriber_management/dev.json")
        last_name = test_data["search_terms"]["existing_subscriber_last_name"]

        with allure.step(f"Search for subscriber '{last_name}'"):
            workflow = SubscriberSearchWorkflow(page, base_url=str(settings.ui.base_url))
            result = workflow.execute(last_name)

        with allure.step("Verify the subscriber was found"):
            SubscriberAssertions.subscriber_found(result, last_name)
            assert result is not None
            assert last_name in result["Last Name"]

    def test_search_nonexistent_subscriber_returns_none(
        self, page, settings: EnvironmentSettings
    ) -> None:
        test_data = TestDataLoader.load_json("subscriber_management/dev.json")
        last_name = test_data["search_terms"]["nonexistent_subscriber_last_name"]

        with allure.step(f"Search for a subscriber that doesn't exist: '{last_name}'"):
            workflow = SubscriberSearchWorkflow(page, base_url=str(settings.ui.base_url))
            result = workflow.execute(last_name)

        with allure.step("Verify no subscriber was found"):
            SubscriberAssertions.subscriber_not_found(result, last_name)

    def test_subscriber_table_has_expected_columns(
        self, page, settings: EnvironmentSettings
    ) -> None:
        test_data = TestDataLoader.load_json("subscriber_management/dev.json")

        with allure.step("Open Subscriber Management"):
            subscriber_page = SubscriberManagementPage(page)
            subscriber_page.base_url = str(settings.ui.base_url)
            subscriber_page.open()

        with allure.step("Verify expected columns and non-empty results"):
            assert subscriber_page.table.headers() == test_data["expected_columns"]
            assert subscriber_page.subscriber_count() > 0
