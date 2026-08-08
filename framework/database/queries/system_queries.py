from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class SystemQueries:
    """All SQL for the `system_config` domain (platform/tenant-level
    configuration — e.g. the "SDS platform modules" / "Sys Admin" area
    referenced in `docs/automation-analysis/ScreenInventory.md`).
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS system_config (
            config_id VARCHAR(64) PRIMARY KEY,
            config_key VARCHAR(128) NOT NULL,
            config_value VARCHAR(256) NOT NULL,
            category VARCHAR(64) NOT NULL,
            updated_by VARCHAR(64) NOT NULL,
            updated_at VARCHAR(32) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS system_config")
    TRUNCATE: TextClause = text("DELETE FROM system_config")

    INSERT: TextClause = text(
        """
        INSERT INTO system_config
            (config_id, config_key, config_value, category, updated_by, updated_at)
        VALUES
            (:config_id, :config_key, :config_value, :category, :updated_by, :updated_at)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM system_config WHERE config_id = :config_id")
    FIND_BY_KEY: TextClause = text("SELECT * FROM system_config WHERE config_key = :config_key")
    FIND_BY_CATEGORY: TextClause = text("SELECT * FROM system_config WHERE category = :category")
    FIND_ALL: TextClause = text("SELECT * FROM system_config ORDER BY config_key")
    UPDATE_VALUE: TextClause = text(
        """
        UPDATE system_config SET config_value = :config_value, updated_by = :updated_by,
            updated_at = :updated_at
        WHERE config_key = :config_key
        """
    )
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM system_config")
