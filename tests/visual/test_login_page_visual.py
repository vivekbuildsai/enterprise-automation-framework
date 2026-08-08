from pathlib import Path

import allure
import pytest

from framework.config import EnvironmentSettings
from framework.exceptions import ValidationError
from framework.pages import LoginPage
from framework.visual import VisualComparator

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def baseline_name(request: pytest.FixtureRequest) -> str:
    """Unique-per-test baseline name/file, and cleaned up before the test
    runs. Two tests (or two parallel xdist workers) must never write to the
    same baseline path — this framework requires parallel execution with no
    shared state, and a shared baseline file is exactly that.
    """
    name = f"visual_{request.node.name}"
    baseline_path = _PROJECT_ROOT / "artifacts" / "visual_baselines" / f"{name}.png"
    baseline_path.unlink(missing_ok=True)
    return name


@allure.feature("Visual Regression")
@pytest.mark.ui
@pytest.mark.visual
class TestLoginPageVisual:
    def test_unchanged_page_matches_its_own_baseline(
        self, page, settings: EnvironmentSettings, baseline_name: str
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()

        with allure.step("Establish baseline"):
            baseline_result = VisualComparator.compare_page(page, baseline_name)
            assert baseline_result.baseline_created is True

        with allure.step("Re-capture the same page and compare"):
            result = VisualComparator.compare_page(page, baseline_name)

        with allure.step("Verify it matches within threshold"):
            VisualComparator.assert_matches(result, threshold=0.5)

    def test_visibly_changed_page_fails_comparison(
        self, page, settings: EnvironmentSettings, baseline_name: str
    ) -> None:
        login_page = LoginPage(page)
        login_page.base_url = str(settings.ui.base_url)
        login_page.open()

        with allure.step("Establish baseline"):
            VisualComparator.compare_page(page, baseline_name)

        with allure.step("Make a deliberate visible change"):
            page.evaluate("document.body.style.backgroundColor = 'red'")

        with allure.step("Verify the comparator flags the mismatch"):
            result = VisualComparator.compare_page(page, baseline_name)
            assert result.diff_percentage > 50
            with pytest.raises(ValidationError, match="Visual regression"):
                VisualComparator.assert_matches(result, threshold=0.5)
