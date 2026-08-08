from __future__ import annotations

import pytest
from sqlalchemy.engine import Connection

from framework.database.enums import DbDialect
from framework.database.exceptions import DatabaseQueryError
from framework.database.utilities.query_executor import QueryExecutor

pytestmark = [pytest.mark.regression, pytest.mark.database]

# Every test below starts with `DROP TABLE IF EXISTS` for its own ad-hoc
# table, and every INSERT supplies an explicit `id` (never relying on
# autoincrement/SERIAL/IDENTITY) — this suite runs against SQLite locally
# (fresh in-memory database per process) but also against real, *persistent*
# PostgreSQL/MySQL servers (docker-compose / CI), where leftover tables and
# SQLite's auto-rowid-on-omitted-id behavior would otherwise make a test
# pass once and then fail on every subsequent run against a real server —
# exactly the class of bug running this suite against real PostgreSQL caught.


def test_execute_ddl_then_select_round_trips(
    db_executor: QueryExecutor, db_connection: Connection
) -> None:
    db_executor.execute("DROP TABLE IF EXISTS t_qe1")
    db_executor.execute("CREATE TABLE t_qe1 (id INTEGER PRIMARY KEY, name TEXT)")
    db_executor.execute_write("INSERT INTO t_qe1 (id, name) VALUES (:id, :n)", {"id": 1, "n": "a"})
    db_connection.commit()

    rows = db_executor.fetch_all("SELECT * FROM t_qe1")
    assert rows == [{"id": 1, "name": "a"}]


def test_fetch_one_returns_none_for_no_rows(db_executor: QueryExecutor) -> None:
    db_executor.execute("DROP TABLE IF EXISTS t_qe2")
    db_executor.execute("CREATE TABLE t_qe2 (id INTEGER)")
    assert db_executor.fetch_one("SELECT * FROM t_qe2") is None


def test_execute_write_returns_affected_row_count(
    db_executor: QueryExecutor, db_connection: Connection
) -> None:
    db_executor.execute("DROP TABLE IF EXISTS t_qe3")
    db_executor.execute("CREATE TABLE t_qe3 (id INTEGER)")
    count = db_executor.execute_write("INSERT INTO t_qe3 (id) VALUES (1), (2), (3)")
    db_connection.commit()
    assert count == 3


def test_invalid_sql_raises_database_query_error(db_executor: QueryExecutor) -> None:
    with pytest.raises(DatabaseQueryError):
        db_executor.execute("SELECT * FROM this_table_does_not_exist_xyz")


def test_execution_result_carries_full_telemetry(db_executor: QueryExecutor, db_key: str) -> None:
    db_executor.execute("DROP TABLE IF EXISTS t_qe4")
    db_executor.execute("CREATE TABLE t_qe4 (id INTEGER)")
    result = db_executor.execute("SELECT * FROM t_qe4")

    assert result.database == db_key
    assert result.dialect in {dialect.value for dialect in DbDialect}
    assert result.elapsed_ms >= 0
    assert result.succeeded is True
    assert result.error is None
    assert "t_qe4" in result.sql
