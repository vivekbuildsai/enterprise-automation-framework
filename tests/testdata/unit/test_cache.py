from __future__ import annotations

import time

import pytest

from framework.testdata.cache import DataCache

pytestmark = pytest.mark.testdata


def test_set_and_get() -> None:
    cache = DataCache()
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_get_missing_key_returns_none() -> None:
    assert DataCache().get("missing") is None


def test_has_distinguishes_missing_from_cached_none() -> None:
    cache = DataCache()
    cache.set("none_key", None)
    assert cache.has("none_key") is True
    assert cache.has("totally_missing") is False


def test_ttl_expiry() -> None:
    cache = DataCache()
    cache.set("expiring", "value", ttl_seconds=0.05)
    assert cache.has("expiring") is True
    time.sleep(0.1)
    assert cache.has("expiring") is False


def test_invalidate_removes_entry() -> None:
    cache = DataCache()
    cache.set("key", "value")
    cache.invalidate("key")
    assert cache.has("key") is False


def test_clear_removes_everything() -> None:
    cache = DataCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.has("a") is False
    assert cache.has("b") is False


def test_get_or_set_only_calls_factory_once() -> None:
    cache = DataCache()
    calls = []

    def factory() -> str:
        calls.append(1)
        return "computed"

    assert cache.get_or_set("k", factory) == "computed"
    assert cache.get_or_set("k", factory) == "computed"
    assert len(calls) == 1
