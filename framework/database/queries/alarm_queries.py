from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class AlarmQueries:
    """All SQL for the `alarms` domain."""

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS alarms (
            alarm_id VARCHAR(64) PRIMARY KEY,
            alarm_code VARCHAR(32) NOT NULL,
            severity VARCHAR(16) NOT NULL,
            entity_type VARCHAR(32) NOT NULL,
            entity_id VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            raised_at VARCHAR(32) NOT NULL,
            cleared_at VARCHAR(32),
            description VARCHAR(256) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS alarms")
    TRUNCATE: TextClause = text("DELETE FROM alarms")

    INSERT: TextClause = text(
        """
        INSERT INTO alarms
            (alarm_id, alarm_code, severity, entity_type, entity_id, status, raised_at,
             cleared_at, description)
        VALUES
            (:alarm_id, :alarm_code, :severity, :entity_type, :entity_id, :status, :raised_at,
             :cleared_at, :description)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM alarms WHERE alarm_id = :alarm_id")
    FIND_ACTIVE: TextClause = text("SELECT * FROM alarms WHERE status = 'ACTIVE'")
    FIND_BY_SEVERITY: TextClause = text("SELECT * FROM alarms WHERE severity = :severity")
    FIND_BY_ENTITY: TextClause = text(
        "SELECT * FROM alarms WHERE entity_type = :entity_type AND entity_id = :entity_id"
    )
    FIND_ALL: TextClause = text("SELECT * FROM alarms ORDER BY raised_at DESC")
    CLEAR_ALARM: TextClause = text(
        "UPDATE alarms SET status = 'CLEARED', cleared_at = :cleared_at WHERE alarm_id = :alarm_id"
    )
    COUNT_ACTIVE: TextClause = text("SELECT COUNT(*) AS c FROM alarms WHERE status = 'ACTIVE'")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM alarms")
