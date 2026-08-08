from __future__ import annotations

from typing import Any

from framework.database.models import Network
from framework.testdata.builders import NetworkBuilder


class NetworkFactory:
    @staticmethod
    def active(**overrides: Any) -> Network:
        return NetworkBuilder().active().with_fields(**overrides).build()

    @staticmethod
    def in_region(ota_region: str, **overrides: Any) -> Network:
        return (
            NetworkBuilder().active().with_ota_region(ota_region).with_fields(**overrides).build()
        )
