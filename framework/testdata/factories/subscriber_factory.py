from __future__ import annotations

from typing import Any

from framework.database.models import Subscriber
from framework.testdata.builders import SubscriberBuilder


class SubscriberFactory:
    """Canned `Subscriber` instances for the common cases — Factory Method
    over `SubscriberBuilder`, for tests that just want "an active
    subscriber" by name rather than chaining `with_x()` calls themselves.
    Every method accepts `**overrides` (field name -> value) for the cases
    that need one field different from the canned default.
    """

    @staticmethod
    def active(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().active().with_fields(**overrides).build()

    @staticmethod
    def suspended(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().suspended().with_fields(**overrides).build()

    @staticmethod
    def blocked(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().blocked().with_fields(**overrides).build()

    @staticmethod
    def premium(**overrides: Any) -> Subscriber:
        return SubscriberBuilder().active().gold_tier().with_fields(**overrides).build()

    @staticmethod
    def new(**overrides: Any) -> Subscriber:
        """A freshly-created subscriber — same as `active()`, named
        separately so scenario code reads as intent ("New Subscriber"
        scenario) rather than an implementation detail.
        """
        return SubscriberFactory.active(**overrides)
