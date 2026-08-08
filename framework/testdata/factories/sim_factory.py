from __future__ import annotations

from typing import Any

from framework.testdata.builders import SIMBuilder
from framework.testdata.builders.models import SimCard


class SimFactory:
    @staticmethod
    def active(**overrides: Any) -> SimCard:
        return SIMBuilder().active().with_fields(**overrides).build()

    @staticmethod
    def inactive(**overrides: Any) -> SimCard:
        return SIMBuilder().inactive().with_fields(**overrides).build()

    @staticmethod
    def blocked(**overrides: Any) -> SimCard:
        return SIMBuilder().blocked().with_fields(**overrides).build()
