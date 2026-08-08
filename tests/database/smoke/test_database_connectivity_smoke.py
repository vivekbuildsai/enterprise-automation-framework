from __future__ import annotations

import allure
import pytest

from framework.database.connection import DatabaseManager

pytestmark = [pytest.mark.smoke, pytest.mark.database]


@allure.feature("Database - Connectivity")
class TestDatabaseConnectivitySmoke:
    def test_health_check_succeeds(self, database_manager: DatabaseManager, db_key: str) -> None:
        with allure.step(f"Health-check '{db_key}'"):
            assert database_manager.health_check(db_key) is True

    def test_engine_is_lazily_created_and_cached(
        self, database_manager: DatabaseManager, db_key: str
    ) -> None:
        first = database_manager.get_engine(db_key)
        second = database_manager.get_engine(db_key)
        assert first is second

    def test_pool_stats_are_reportable(
        self, database_manager: DatabaseManager, db_key: str
    ) -> None:
        stats = database_manager.pool_stats(db_key)
        assert stats.pool_class

    def test_health_check_returns_false_for_unknown_db_key(
        self, database_manager: DatabaseManager
    ) -> None:
        assert database_manager.health_check("does_not_exist_in_config") is False
