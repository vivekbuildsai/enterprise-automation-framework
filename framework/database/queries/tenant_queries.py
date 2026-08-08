from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

# Column/type choices here are deliberately dialect-portable (VARCHAR over
# SERIAL/IDENTITY, ISO-8601 strings over native TIMESTAMP) so the exact same
# DDL runs unmodified on SQLite/PostgreSQL/MySQL/Oracle/SQL Server — see
# docs/DatabaseFramework.md "Demo schema" for why, and that this is a
# representative schema for proving framework capability, not any specific
# customer's real database schema.


class TenantQueries:
    """All SQL for the `tenants` domain. No SQL lives outside this module —
    repositories/tests only ever call these named statements.
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id VARCHAR(64) PRIMARY KEY,
            tenant_code VARCHAR(32) NOT NULL,
            tenant_name VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL,
            created_at VARCHAR(32) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS tenants")
    TRUNCATE: TextClause = text("DELETE FROM tenants")

    INSERT: TextClause = text(
        """
        INSERT INTO tenants (tenant_id, tenant_code, tenant_name, status, created_at)
        VALUES (:tenant_id, :tenant_code, :tenant_name, :status, :created_at)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM tenants WHERE tenant_id = :tenant_id")
    FIND_BY_CODE: TextClause = text("SELECT * FROM tenants WHERE tenant_code = :tenant_code")
    FIND_BY_STATUS: TextClause = text("SELECT * FROM tenants WHERE status = :status")
    FIND_ALL: TextClause = text("SELECT * FROM tenants ORDER BY tenant_code")
    UPDATE_STATUS: TextClause = text(
        "UPDATE tenants SET status = :status WHERE tenant_id = :tenant_id"
    )
    DELETE_BY_ID: TextClause = text("DELETE FROM tenants WHERE tenant_id = :tenant_id")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM tenants")
