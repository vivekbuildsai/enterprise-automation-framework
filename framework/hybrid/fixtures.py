from __future__ import annotations

import pytest

from framework.config import EnvironmentSettings
from framework.hybrid.validation_facade import ValidationFacade


@pytest.fixture
def validation_facade(settings: EnvironmentSettings) -> ValidationFacade:
    """The one fixture a hybrid test needs beyond its normal `page`/API/DB
    fixtures: wraps `settings.validation_mode` so `facade.verify_api(...)`/
    `facade.verify_database(...)` calls in the test body run or no-op purely
    based on config — see `ValidationFacade` for the full contract.
    """
    return ValidationFacade(settings.validation_mode)
