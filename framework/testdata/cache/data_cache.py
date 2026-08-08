from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float | None


class DataCache:
    """In-memory cache for loaded/generated test data within a session —
    so re-requesting the same dataset (e.g. via `DatasetRegistry`, or a
    provider hit repeatedly across many tests) doesn't re-read a file or
    re-query a database every time. Entries without a TTL never expire on
    their own; call `invalidate`/`clear` explicitly for those. Uses a
    sentinel (not `None`) to distinguish "not cached" from "cached value
    is `None`", so a legitimately `None` lookup result caches correctly.
    """

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        self._entries[key] = _CacheEntry(value=value, expires_at=expires_at)

    def get(self, key: str) -> Any:
        value = self._get_or_missing(key)
        return None if value is _MISSING else value

    def has(self, key: str) -> bool:
        return self._get_or_missing(key) is not _MISSING

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def get_or_set(self, key: str, factory: Any, *, ttl_seconds: float | None = None) -> Any:
        """`factory` is a zero-arg callable, only invoked on a cache miss."""
        cached = self._get_or_missing(key)
        if cached is not _MISSING:
            return cached
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value

    def _get_or_missing(self, key: str) -> Any:
        entry = self._entries.get(key)
        if entry is None:
            return _MISSING
        if entry.expires_at is not None and time.monotonic() >= entry.expires_at:
            del self._entries[key]
            return _MISSING
        return entry.value


cache = DataCache()
