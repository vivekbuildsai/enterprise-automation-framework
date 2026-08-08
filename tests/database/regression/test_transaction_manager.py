from __future__ import annotations

import pytest
from sqlalchemy.engine import Connection

from framework.database.enums import TransactionMode
from framework.database.exceptions import TransactionError
from framework.database.utilities.query_executor import QueryExecutor
from framework.database.utilities.transaction_manager import TransactionManager

pytestmark = [pytest.mark.regression, pytest.mark.database]

# Every test drops its own ad-hoc table (outside/before the transaction
# under test) and commits before proceeding — this suite runs against both
# SQLite (fresh in-memory database per process) and real, *persistent*
# PostgreSQL/MySQL servers (docker-compose / CI), where a leftover table
# from a previous run would otherwise make `CREATE TABLE` fail with
# "already exists" the second time this suite runs against a real server.


def _reset_table(executor: QueryExecutor, connection: Connection, table: str) -> None:
    executor.execute(f"DROP TABLE IF EXISTS {table}")
    connection.commit()


def test_commit_mode_persists_changes(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    _reset_table(db_executor, db_connection, "t_tx1")

    tx = TransactionManager(db_connection, db_key="test")
    with tx.transaction():
        db_executor.execute("CREATE TABLE t_tx1 (id INTEGER)")
        db_executor.execute_write("INSERT INTO t_tx1 VALUES (1)")

    assert db_executor.fetch_all("SELECT * FROM t_tx1") == [{"id": 1}]


def test_rollback_mode_always_discards_changes(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    _reset_table(db_executor, db_connection, "t_tx2")
    db_executor.execute("CREATE TABLE t_tx2 (id INTEGER)")
    db_connection.commit()

    tx = TransactionManager(db_connection, db_key="test")
    with tx.transaction(mode=TransactionMode.ROLLBACK):
        db_executor.execute_write("INSERT INTO t_tx2 VALUES (1)")

    assert db_executor.fetch_all("SELECT * FROM t_tx2") == []


def test_read_only_mode_also_discards_changes(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    _reset_table(db_executor, db_connection, "t_tx3")
    db_executor.execute("CREATE TABLE t_tx3 (id INTEGER)")
    db_connection.commit()

    tx = TransactionManager(db_connection, db_key="test")
    with tx.transaction(mode=TransactionMode.READ_ONLY):
        db_executor.execute_write("INSERT INTO t_tx3 VALUES (1)")

    assert db_executor.fetch_all("SELECT * FROM t_tx3") == []


def test_exception_inside_transaction_rolls_back(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    _reset_table(db_executor, db_connection, "t_tx4")
    db_executor.execute("CREATE TABLE t_tx4 (id INTEGER)")
    db_connection.commit()

    tx = TransactionManager(db_connection, db_key="test")
    with pytest.raises(RuntimeError), tx.transaction():
        db_executor.execute_write("INSERT INTO t_tx4 VALUES (1)")
        raise RuntimeError("simulated failure")

    assert db_executor.fetch_all("SELECT * FROM t_tx4") == []


def test_nested_transaction_rolls_back_independently_of_outer(
    db_connection: Connection, db_executor: QueryExecutor
) -> None:
    _reset_table(db_executor, db_connection, "t_tx5")
    db_executor.execute("CREATE TABLE t_tx5 (id INTEGER)")
    db_connection.commit()

    tx = TransactionManager(db_connection, db_key="test")
    with tx.transaction():
        db_executor.execute_write("INSERT INTO t_tx5 VALUES (1)")
        with pytest.raises(RuntimeError), tx.nested_transaction():
            db_executor.execute_write("INSERT INTO t_tx5 VALUES (2)")
            raise RuntimeError("savepoint failure")

    rows = db_executor.fetch_all("SELECT * FROM t_tx5")
    assert [row["id"] for row in rows] == [1]


def test_nested_transaction_without_outer_transaction_raises(db_connection: Connection) -> None:
    tx = TransactionManager(db_connection, db_key="test")
    with pytest.raises(TransactionError), tx.nested_transaction():
        pass
