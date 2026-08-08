from __future__ import annotations

from framework.auth import auth_state_manager
from framework.config import settings
from framework.drivers import driver_manager
from framework.logger import logger
from framework.models import dashboard_config
from framework.project_root import PROJECT_ROOT
from framework.testdata.datasets import dataset_loader
from framework.utilities import screenshot_utils, test_data_loader
from framework.visual import visual_comparator


def test_settings_config_dir_is_under_project_root() -> None:
    assert settings._CONFIG_DIR == PROJECT_ROOT / "config" / "environments"


def test_driver_manager_artifacts_dir_is_under_project_root() -> None:
    assert driver_manager._ARTIFACTS_DIR == PROJECT_ROOT / "artifacts"


def test_logger_log_dir_is_under_project_root() -> None:
    assert logger._LOG_DIR == PROJECT_ROOT / "logs"


def test_auth_state_manager_default_dir_is_under_project_root() -> None:
    assert auth_state_manager.AuthStateManager()._dir == PROJECT_ROOT / ".auth"


def test_dataset_loader_testdata_dir_is_under_project_root() -> None:
    assert dataset_loader._TESTDATA_DIR == PROJECT_ROOT / "data" / "testdata"


def test_test_data_loader_testdata_dir_is_under_project_root() -> None:
    assert test_data_loader._TESTDATA_DIR == PROJECT_ROOT / "data" / "testdata"


def test_dashboard_config_dashboards_dir_is_under_project_root() -> None:
    assert dashboard_config._DASHBOARDS_DIR == PROJECT_ROOT / "config" / "dashboards"


def test_screenshot_utils_screenshots_dir_is_under_project_root() -> None:
    assert screenshot_utils._SCREENSHOTS_DIR == PROJECT_ROOT / "artifacts" / "screenshots"


def test_visual_comparator_baselines_and_diffs_dirs_are_under_project_root() -> None:
    assert visual_comparator._BASELINES_DIR == PROJECT_ROOT / "artifacts" / "visual_baselines"
    assert visual_comparator._DIFFS_DIR == PROJECT_ROOT / "artifacts" / "visual_diffs"
