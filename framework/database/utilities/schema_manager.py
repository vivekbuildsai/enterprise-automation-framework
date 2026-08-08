from __future__ import annotations

from framework.database.queries import (
    AlarmQueries,
    AuditQueries,
    NetworkQueries,
    SteeringQueries,
    SubscriberQueries,
    SystemQueries,
    TenantQueries,
)
from framework.database.utilities.query_executor import QueryExecutor

# No FOREIGN KEY constraints are declared in any CREATE_TABLE statement —
# deliberate, since enforcing/naming FKs is one of the few things that
# genuinely differs across SQLite/PostgreSQL/MySQL/Oracle/SQL Server DDL.
# This is a representative demo schema for proving framework capability
# (see docs/DatabaseFramework.md), not any specific customer's real schema,
# so keeping it FK-free keeps create/drop/truncate ordering irrelevant across all five
# dialects instead of encoding a dependency graph that doesn't reflect any
# confirmed real schema anyway.
_CREATE_STATEMENTS = (
    TenantQueries.CREATE_TABLE,
    NetworkQueries.CREATE_TABLE,
    SubscriberQueries.CREATE_TABLE,
    SteeringQueries.CREATE_TABLE,
    AuditQueries.CREATE_TABLE,
    AlarmQueries.CREATE_TABLE,
    SystemQueries.CREATE_TABLE,
)
_DROP_STATEMENTS = (
    TenantQueries.DROP_TABLE,
    NetworkQueries.DROP_TABLE,
    SubscriberQueries.DROP_TABLE,
    SteeringQueries.DROP_TABLE,
    AuditQueries.DROP_TABLE,
    AlarmQueries.DROP_TABLE,
    SystemQueries.DROP_TABLE,
)
_TRUNCATE_STATEMENTS = (
    SteeringQueries.TRUNCATE,
    SubscriberQueries.TRUNCATE,
    NetworkQueries.TRUNCATE,
    TenantQueries.TRUNCATE,
    AuditQueries.TRUNCATE,
    AlarmQueries.TRUNCATE,
    SystemQueries.TRUNCATE,
)


class SchemaManager:
    """Creates, drops, and truncates the framework's demo schema — the 7
    domain tables every repository/validator/test in this milestone is
    built and verified against.
    """

    @staticmethod
    def create_all(executor: QueryExecutor) -> None:
        for statement in _CREATE_STATEMENTS:
            executor.execute(statement)

    @staticmethod
    def drop_all(executor: QueryExecutor) -> None:
        for statement in _DROP_STATEMENTS:
            executor.execute(statement)

    @staticmethod
    def truncate_all(executor: QueryExecutor) -> None:
        for statement in _TRUNCATE_STATEMENTS:
            executor.execute(statement)
