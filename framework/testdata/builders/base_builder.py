from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Self, TypeVar

T = TypeVar("T")


class BaseBuilder(ABC, Generic[T]):
    """Common fluent-builder scaffolding every domain builder
    (`SubscriberBuilder`, `TenantBuilder`, ...) is built on.

    Subclasses store explicitly-set field values in `self._fields` via
    `_set(**kwargs)` (returns `self`, enabling chaining) and implement
    `build()` to assemble `T`, filling in a freshly-generated default for
    any field the caller never set. Because defaults are generated lazily
    inside `build()` rather than eagerly at construction time, calling
    `build()` more than once on the same builder produces independent
    records that share only the fields explicitly overridden — which is
    what makes `build_many()` useful for bulk data instead of producing
    `count` identical copies.
    """

    def __init__(self) -> None:
        self._fields: dict[str, Any] = {}

    def _set(self, **kwargs: Any) -> Self:
        self._fields.update(kwargs)
        return self

    def with_fields(self, **kwargs: Any) -> Self:
        """Public escape hatch for setting arbitrary fields by name —
        for generic callers (factories, scenario composition) that accept
        `**overrides` without knowing which `with_x()` methods a specific
        builder subclass exposes. Prefer the named `with_x()` methods in
        test code itself; this exists for framework-level code that must
        stay builder-agnostic.
        """
        return self._set(**kwargs)

    def _get(self, field: str, default_factory: Any) -> Any:
        """Returns the explicitly-set value for `field`, or calls
        `default_factory()` to lazily generate one.
        """
        if field in self._fields:
            return self._fields[field]
        return default_factory()

    @abstractmethod
    def build(self) -> T:
        raise NotImplementedError

    def build_many(self, count: int) -> list[T]:
        return [self.build() for _ in range(count)]
