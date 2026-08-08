from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from framework.logger import get_logger

_logger = get_logger("ConnectionPool")


@dataclass(frozen=True, slots=True)
class PoolStats:
    """Point-in-time snapshot of an engine's connection pool — attached to
    Allure reports (`framework.database.telemetry`) and logged on demand so
    pool exhaustion shows up as data, not just a timeout stack trace.
    """

    pool_class: str
    size: int
    checked_in: int
    checked_out: int
    overflow: int


class ConnectionPoolManager:
    """Thin wrapper over an `Engine`'s connection pool: exposes read-only
    stats for reporting/diagnostics and owns disposal. Kept separate from
    `DatabaseManager` (which owns *which* engine to use) so pool-level
    concerns — stats, disposal — have one obvious home instead of being
    scattered across engine-cache logic.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def stats(self) -> PoolStats:
        pool = self._engine.pool
        # StaticPool/NullPool (used for SQLite) don't implement size()/
        # checkedin()/etc. — fall back to 0s rather than raising, since pool
        # stats are diagnostic sugar, not something callers should have to
        # guard for per-dialect.
        return PoolStats(
            pool_class=type(pool).__name__,
            size=getattr(pool, "size", lambda: 0)(),
            checked_in=getattr(pool, "checkedin", lambda: 0)(),
            checked_out=getattr(pool, "checkedout", lambda: 0)(),
            overflow=getattr(pool, "overflow", lambda: 0)(),
        )

    def dispose(self) -> None:
        _logger.info(f"Disposing connection pool ({type(self._engine.pool).__name__})")
        self._engine.dispose()
