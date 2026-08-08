from __future__ import annotations

from typing import Any

from framework.database.models import Alarm
from framework.testdata.builders import AlarmBuilder


class AlarmFactory:
    @staticmethod
    def critical(**overrides: Any) -> Alarm:
        return AlarmBuilder().critical().active().with_fields(**overrides).build()

    @staticmethod
    def cleared(**overrides: Any) -> Alarm:
        return AlarmBuilder().cleared().with_fields(**overrides).build()

    @staticmethod
    def network_failure(network_id: str, **overrides: Any) -> Alarm:
        return (
            AlarmBuilder()
            .critical()
            .active()
            .with_entity("NETWORK", network_id)
            .with_description("Network failure detected")
            .with_fields(**overrides)
            .build()
        )
