from __future__ import annotations

from typing import Any

from framework.database.models import SteeringZone
from framework.testdata.builders import SteeringRuleBuilder


class SteeringRuleFactory:
    @staticmethod
    def normal(**overrides: Any) -> SteeringZone:
        return SteeringRuleBuilder().with_fields(**overrides).build()

    @staticmethod
    def with_leakage(**overrides: Any) -> SteeringZone:
        return SteeringRuleBuilder().with_leakage().with_fields(**overrides).build()

    @staticmethod
    def anti_sor(**overrides: Any) -> SteeringZone:
        return SteeringRuleBuilder().with_anti_sor().with_fields(**overrides).build()

    @staticmethod
    def network_failure(**overrides: Any) -> SteeringZone:
        return (
            SteeringRuleBuilder()
            .with_status("DEGRADED")
            .with_roamer_count(0)
            .with_data_usage_mb(0)
            .with_fields(**overrides)
            .build()
        )
