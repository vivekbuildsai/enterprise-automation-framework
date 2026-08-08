import allure
import pytest

from framework.accessibility import AccessibilityChecker
from framework.config import EnvironmentSettings
from framework.exceptions import ValidationError
from framework.pages import LoginPage


@allure.feature("Accessibility")
@pytest.mark.ui
@pytest.mark.accessibility
class TestLoginPageAccessibility:
    def test_scan_detects_known_color_contrast_issue(
        self, page, settings: EnvironmentSettings
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()

        with allure.step("Run axe-core accessibility scan"):
            results = AccessibilityChecker.run(page)

        with allure.step("Verify the scan surfaces real violations, not a silent pass"):
            assert results.violations_count > 0
            violation_ids = {v["id"] for v in results.response["violations"]}
            assert "color-contrast" in violation_ids

    def test_check_raises_on_serious_violations(self, page, settings: EnvironmentSettings) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()

        with (
            allure.step("Assert the page fails an accessibility gate on serious violations"),
            pytest.raises(ValidationError, match="color-contrast"),
        ):
            AccessibilityChecker.check(page)

    def test_check_passes_when_scoped_to_critical_only(
        self, page, settings: EnvironmentSettings
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()

        with allure.step(
            "Verify severity gating is configurable (no 'critical' violations on this page)"
        ):
            AccessibilityChecker.check(page, failing_impacts=frozenset({"critical"}))
