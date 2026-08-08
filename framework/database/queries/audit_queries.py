from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class AuditQueries:
    """All SQL for the `audit_log` domain — the application's own audit
    trail (e.g. "Modified by: Admin" fields, failed-login records), distinct
    from `framework.database.audit.AuditLogger` which logs this
    *framework's own* database activity.
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id VARCHAR(64) PRIMARY KEY,
            entity_type VARCHAR(32) NOT NULL,
            entity_id VARCHAR(64) NOT NULL,
            action VARCHAR(32) NOT NULL,
            performed_by VARCHAR(64) NOT NULL,
            performed_at VARCHAR(32) NOT NULL,
            details VARCHAR(512) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS audit_log")
    TRUNCATE: TextClause = text("DELETE FROM audit_log")

    INSERT: TextClause = text(
        """
        INSERT INTO audit_log
            (audit_id, entity_type, entity_id, action, performed_by, performed_at, details)
        VALUES
            (:audit_id, :entity_type, :entity_id, :action, :performed_by, :performed_at, :details)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM audit_log WHERE audit_id = :audit_id")
    FIND_BY_ENTITY: TextClause = text(
        "SELECT * FROM audit_log WHERE entity_type = :entity_type AND entity_id = :entity_id "
        "ORDER BY performed_at DESC"
    )
    FIND_BY_PERFORMER: TextClause = text(
        "SELECT * FROM audit_log WHERE performed_by = :performed_by ORDER BY performed_at DESC"
    )
    FIND_ALL: TextClause = text("SELECT * FROM audit_log ORDER BY performed_at DESC")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM audit_log")
