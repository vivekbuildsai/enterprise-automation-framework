from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause


class SteeringQueries:
    """All SQL for the `steering_zones` domain — an illustrative example
    domain (zone/class-of-service/traffic-redirection routing rules) used
    to exercise the database validation layer end to end. Swapping in a
    real application's schema later is a column-mapping exercise against
    `SteeringZone` (`framework.database.models`), not a redesign.
    """

    CREATE_TABLE: TextClause = text(
        """
        CREATE TABLE IF NOT EXISTS steering_zones (
            zone_id VARCHAR(64) PRIMARY KEY,
            zone_code VARCHAR(64) NOT NULL,
            country VARCHAR(64) NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            network_id VARCHAR(64) NOT NULL,
            tr_type VARCHAR(16) NOT NULL,
            cos VARCHAR(32) NOT NULL,
            ota_region VARCHAR(32) NOT NULL,
            roamer_count INTEGER NOT NULL,
            data_usage_mb INTEGER NOT NULL,
            leakage_flag INTEGER NOT NULL,
            anti_sor_flag INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL,
            modified_by VARCHAR(64) NOT NULL,
            modified_date VARCHAR(32) NOT NULL
        )
        """
    )
    DROP_TABLE: TextClause = text("DROP TABLE IF EXISTS steering_zones")
    TRUNCATE: TextClause = text("DELETE FROM steering_zones")

    INSERT: TextClause = text(
        """
        INSERT INTO steering_zones
            (zone_id, zone_code, country, tenant_id, network_id, tr_type, cos, ota_region,
             roamer_count, data_usage_mb, leakage_flag, anti_sor_flag, status,
             modified_by, modified_date)
        VALUES
            (:zone_id, :zone_code, :country, :tenant_id, :network_id, :tr_type, :cos, :ota_region,
             :roamer_count, :data_usage_mb, :leakage_flag, :anti_sor_flag, :status,
             :modified_by, :modified_date)
        """
    )
    FIND_BY_ID: TextClause = text("SELECT * FROM steering_zones WHERE zone_id = :zone_id")
    FIND_BY_TENANT: TextClause = text("SELECT * FROM steering_zones WHERE tenant_id = :tenant_id")
    FIND_BY_NETWORK: TextClause = text(
        "SELECT * FROM steering_zones WHERE network_id = :network_id"
    )
    FIND_WITH_LEAKAGE: TextClause = text(
        "SELECT * FROM steering_zones WHERE tenant_id = :tenant_id AND leakage_flag = 1"
    )
    FIND_ANTI_SOR: TextClause = text(
        "SELECT * FROM steering_zones WHERE tenant_id = :tenant_id AND anti_sor_flag = 1"
    )
    FIND_ALL: TextClause = text("SELECT * FROM steering_zones ORDER BY zone_code")
    UPDATE_STATUS: TextClause = text(
        """
        UPDATE steering_zones SET status = :status, modified_by = :modified_by,
            modified_date = :modified_date
        WHERE zone_id = :zone_id
        """
    )
    DELETE_BY_ID: TextClause = text("DELETE FROM steering_zones WHERE zone_id = :zone_id")
    COUNT_ALL: TextClause = text("SELECT COUNT(*) AS c FROM steering_zones")
    SUM_ROAMER_COUNT_BY_TENANT: TextClause = text(
        "SELECT COALESCE(SUM(roamer_count), 0) AS total FROM steering_zones "
        "WHERE tenant_id = :tenant_id"
    )
