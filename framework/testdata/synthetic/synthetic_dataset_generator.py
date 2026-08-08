from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from framework.testdata.builders.base_builder import BaseBuilder

T = TypeVar("T")


class SyntheticDatasetGenerator:
    """Bulk-generates volume/load test data from any builder. Thin,
    explicitly-named wrapper over `BaseBuilder.build_many()` — exists so a
    call site that's specifically about generating volume data reads that
    way, rather than an incidental `.build_many()` call buried in test
    logic.
    """

    @staticmethod
    def generate(builder: BaseBuilder[T], count: int) -> list[T]:
        return builder.build_many(count)

    @staticmethod
    def generate_with_variation(
        builder_factory: Callable[[], BaseBuilder[T]], count: int
    ) -> list[T]:
        """`builder_factory` returns a *fresh* builder each call (e.g.
        `lambda: SubscriberBuilder().gold_tier()`) — for records that each
        need their own independently configured builder rather than
        sharing one builder's fixed field overrides across every record.
        """
        return [builder_factory().build() for _ in range(count)]
