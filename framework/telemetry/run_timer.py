from __future__ import annotations

import secrets
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field

from framework.logger import get_logger

_logger = get_logger("RunTimer")


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    name: str
    seconds: float


@dataclass(slots=True)
class RunTimer:
    """Lightweight, in-process phase-timing for one CLI invocation (a
    Discovery/Sync/validate run) — not a metrics platform, not persisted
    anywhere: just a short run ID plus a list of named phase durations,
    logged as one readable summary at the end. Deliberately has zero
    dependencies beyond the framework's own logger and stdlib `time`, so
    it adds no measurable overhead of its own and nothing new to install
    or configure.

    Usage::

        timer = RunTimer()
        with timer.phase("Browser startup"):
            ...
        with timer.phase("Navigation"):
            ...
        timer.log_summary()
    """

    run_id: str = field(default_factory=lambda: f"RUN-{secrets.token_hex(2).upper()}")
    _phases: list[PhaseTiming] = field(default_factory=list)

    @contextmanager
    def phase(self, name: str) -> Generator[None, None, None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self._phases.append(PhaseTiming(name=name, seconds=time.perf_counter() - start))

    @property
    def phases(self) -> list[PhaseTiming]:
        return list(self._phases)

    @property
    def total_seconds(self) -> float:
        return sum(p.seconds for p in self._phases)

    def summary(self) -> str:
        """Renders the same fixed-width table shown in the framework's
        observability docs — a name column, a right-aligned seconds
        column, and a total row, nothing more.
        """
        if not self._phases:
            return f"{self.run_id}\n\n(no phases recorded)"

        name_width = max(len(p.name) for p in (*self._phases, PhaseTiming("Total", 0.0)))
        lines = [self.run_id, ""]
        for p in self._phases:
            lines.append(f"{p.name.ljust(name_width)}   {p.seconds:.2f}s")
        lines.append("-" * (name_width + 10))
        lines.append(f"{'Total'.ljust(name_width)}   {self.total_seconds:.2f}s")
        return "\n".join(lines)

    def log_summary(self) -> None:
        _logger.info("\n" + self.summary())
