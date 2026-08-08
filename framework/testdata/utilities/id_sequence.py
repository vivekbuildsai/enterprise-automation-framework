from __future__ import annotations

import threading


class IdSequenceGenerator:
    """Thread-safe incrementing counter for deterministic, unique IDs within
    a test run — e.g. `TENANT-{seq}` style identifiers where "unique within
    this run" matters more than "globally unique" (that's what `RandomData.
    uuid()` is for). One instance per named sequence so unrelated entities
    don't compete for the same counter.
    """

    def __init__(self, *, start: int = 1) -> None:
        self._value = start - 1
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def next_id(self, *, prefix: str = "", width: int = 0) -> str:
        """`next_id(prefix="SUB")` -> "SUB-1", "SUB-2", ...; `width=4` zero-pads
        the numeric part ("SUB-0001").
        """
        n = self.next()
        number = str(n).zfill(width) if width else str(n)
        return f"{prefix}-{number}" if prefix else number

    def reset(self, *, start: int = 1) -> None:
        with self._lock:
            self._value = start - 1


class SequenceRegistry:
    """Named registry of `IdSequenceGenerator` instances so unrelated
    builders (`SubscriberBuilder`, `TenantBuilder`, ...) each get their own
    counter without every module needing to construct and pass one around.
    """

    def __init__(self) -> None:
        self._sequences: dict[str, IdSequenceGenerator] = {}
        self._lock = threading.Lock()

    def get(self, name: str) -> IdSequenceGenerator:
        with self._lock:
            if name not in self._sequences:
                self._sequences[name] = IdSequenceGenerator()
            return self._sequences[name]

    def reset_all(self) -> None:
        with self._lock:
            for sequence in self._sequences.values():
                sequence.reset()


sequences = SequenceRegistry()
