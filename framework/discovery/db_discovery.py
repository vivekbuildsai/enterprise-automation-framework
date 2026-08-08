from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from framework.discovery.models import DiscoveredColumn, DiscoveredTable
from framework.logger import get_logger

_logger = get_logger("DatabaseDiscoveryEngine")


class DatabaseDiscoveryEngine:
    """Read-only schema reflection via SQLAlchemy's `Inspector` — the
    standard, safe way to discover a database's real structure from an
    authorized connection (typically `DatabaseManager.get_engine(db_key)`).
    Only ever runs metadata queries (`information_schema`/the dialect
    equivalent), never DDL/DML, and never invents a table/column that
    reflection doesn't confirm exists.
    """

    def __init__(self, engine: Engine) -> None:
        self._inspector = inspect(engine)

    def discover_tables(self) -> list[DiscoveredTable]:
        tables = [self._discover_table(name) for name in self._inspector.get_table_names()]
        _logger.info(f"Discovered {len(tables)} tables")
        return tables

    def _discover_table(self, table_name: str) -> DiscoveredTable:
        pk_columns = set(
            self._inspector.get_pk_constraint(table_name).get("constrained_columns") or []
        )
        columns = [
            DiscoveredColumn(
                name=column["name"],
                type=str(column["type"]),
                nullable=column.get("nullable", True),
                primary_key=column["name"] in pk_columns,
            )
            for column in self._inspector.get_columns(table_name)
        ]
        foreign_keys = [
            f"{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}"
            for fk in self._inspector.get_foreign_keys(table_name)
        ]
        return DiscoveredTable(name=table_name, columns=columns, foreign_keys=foreign_keys)
