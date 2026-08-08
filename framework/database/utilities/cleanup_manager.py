from __future__ import annotations

from framework.database.utilities.query_executor import QueryExecutor
from framework.database.utilities.schema_manager import SchemaManager


class CleanupManager:
    """Leaves the demo schema's tables empty (but still created) — the
    counterpart to `SeedManager`, used between tests or at suite teardown so
    the next test starts from a known-empty state without paying
    schema-creation cost again. Thin by design: delegates to
    `SchemaManager.truncate_all`, which already owns table-order/DDL
    concerns — this class exists as the named, seed/cleanup-symmetric entry
    point the database layer's fixtures call.
    """

    @staticmethod
    def truncate_all(executor: QueryExecutor) -> None:
        SchemaManager.truncate_all(executor)
