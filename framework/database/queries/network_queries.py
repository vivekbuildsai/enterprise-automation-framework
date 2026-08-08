from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class NetworkQueries:
    """All SQL for the `networks` domain (see `TenantQueries` module
    docstring for the dialect-portability rationale behind the schema).
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS networks (
            network_id VARCHAR(64) PRIMARY KEY,
            network_code VARCHAR(32) NOT NULL,
            network_name VARCHAR(128) NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            ota_region VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS networks")
    TRUNCATE: TextClause = text("DELETE FROM networks")

    INSERT: TextClause = text(
        """
        INSERT INTO networks (network_id, network_code, network_name, tenant_id, ota_region, status)
        VALUES (:network_id, :network_code, :network_name, :tenant_id, :ota_region, :status)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM networks WHERE network_id = :network_id")
    FIND_BY_TENANT: TextClause = text("SELECT * FROM networks WHERE tenant_id = :tenant_id")
    FIND_BY_OTA_REGION: TextClause = text("SELECT * FROM networks WHERE ota_region = :ota_region")
    FIND_ALL: TextClause = text("SELECT * FROM networks ORDER BY network_code")
    UPDATE_STATUS: TextClause = text(
        "UPDATE networks SET status = :status WHERE network_id = :network_id"
    )
    DELETE_BY_ID: TextClause = text("DELETE FROM networks WHERE network_id = :network_id")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM networks")
