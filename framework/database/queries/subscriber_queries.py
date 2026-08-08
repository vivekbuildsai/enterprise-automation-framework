from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class SubscriberQueries:
    """All SQL for the `subscribers` domain (see `TenantQueries` module
    docstring for the dialect-portability rationale behind the schema).
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS subscribers (
            subscriber_id VARCHAR(64) PRIMARY KEY,
            msisdn VARCHAR(32) NOT NULL,
            imsi VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL,
            cos VARCHAR(32) NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            network_id VARCHAR(64) NOT NULL,
            created_at VARCHAR(32) NOT NULL,
            updated_at VARCHAR(32) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS subscribers")
    TRUNCATE: TextClause = text("DELETE FROM subscribers")

    INSERT: TextClause = text(
        """
        INSERT INTO subscribers
            (subscriber_id, msisdn, imsi, status, cos, tenant_id, network_id,
             created_at, updated_at)
        VALUES
            (:subscriber_id, :msisdn, :imsi, :status, :cos, :tenant_id, :network_id,
             :created_at, :updated_at)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM subscribers WHERE subscriber_id = :subscriber_id")
    FIND_BY_MSISDN: TextClause = text("SELECT * FROM subscribers WHERE msisdn = :msisdn")
    FIND_BY_TENANT: TextClause = text("SELECT * FROM subscribers WHERE tenant_id = :tenant_id")
    FIND_BY_STATUS: TextClause = text("SELECT * FROM subscribers WHERE status = :status")
    FIND_ALL: TextClause = text("SELECT * FROM subscribers ORDER BY msisdn")
    UPDATE_STATUS: TextClause = text(
        """
        UPDATE subscribers SET status = :status, updated_at = :updated_at
        WHERE subscriber_id = :subscriber_id
        """
    )
    DELETE_BY_ID: TextClause = text("DELETE FROM subscribers WHERE subscriber_id = :subscriber_id")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM subscribers")
    COUNT_BY_STATUS: TextClause = text(
        "SELECT COUNT(*) AS c FROM subscribers WHERE status = :status"
    )
