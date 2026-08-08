from __future__ import annotations

from datetime import UTC, datetime

from framework.database.models import SteeringZone
from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.utilities.id_sequence import sequences
from framework.utilities.random_data import RandomData

_zone_sequence = sequences.get("steering_zone")

_TR_TYPES = ("LBTR", "SRDC")
_OTA_REGIONS = ("EMEA", "EU", "APAC", "AMER")


class SteeringRuleBuilder(BaseBuilder[SteeringZone]):
    """Fluent builder for `framework.database.models.SteeringZone` — the
    Steering of Roaming domain (`docs/DatabaseFramework.md`), covering the
    fields the real Steering Overview screen surfaces (TR type, CoS, OTA
    region, roamer count/data usage, leakage, Anti-SoR).
    """

    def with_zone_id(self, zone_id: str) -> SteeringRuleBuilder:
        return self._set(zone_id=zone_id)

    def with_zone_code(self, zone_code: str) -> SteeringRuleBuilder:
        return self._set(zone_code=zone_code)

    def with_country(self, country: str) -> SteeringRuleBuilder:
        return self._set(country=country)

    def with_tenant_id(self, tenant_id: str) -> SteeringRuleBuilder:
        return self._set(tenant_id=tenant_id)

    def with_network_id(self, network_id: str) -> SteeringRuleBuilder:
        return self._set(network_id=network_id)

    def with_tr_type(self, tr_type: str) -> SteeringRuleBuilder:
        return self._set(tr_type=tr_type)

    def with_cos(self, cos: str) -> SteeringRuleBuilder:
        return self._set(cos=cos)

    def with_ota_region(self, ota_region: str) -> SteeringRuleBuilder:
        return self._set(ota_region=ota_region)

    def with_roamer_count(self, roamer_count: int) -> SteeringRuleBuilder:
        return self._set(roamer_count=roamer_count)

    def with_data_usage_mb(self, data_usage_mb: int) -> SteeringRuleBuilder:
        return self._set(data_usage_mb=data_usage_mb)

    def with_status(self, status: str) -> SteeringRuleBuilder:
        return self._set(status=status)

    def with_modified_by(self, modified_by: str) -> SteeringRuleBuilder:
        return self._set(modified_by=modified_by)

    def with_leakage(self, *, has_leakage: bool = True) -> SteeringRuleBuilder:
        return self._set(leakage_flag=1 if has_leakage else 0)

    def with_anti_sor(self, *, is_anti_sor: bool = True) -> SteeringRuleBuilder:
        return self._set(anti_sor_flag=1 if is_anti_sor else 0)

    def build(self) -> SteeringZone:
        now = datetime.now(UTC).isoformat()
        return SteeringZone(
            zone_id=self._get("zone_id", lambda: _zone_sequence.next_id(prefix="ZONE")),
            zone_code=self._get("zone_code", lambda: f"Country_{RandomData.random_int(1, 999)}"),
            country=self._get("country", RandomData.country),
            tenant_id=self._get("tenant_id", lambda: "TENANT-1"),
            network_id=self._get("network_id", lambda: "NETWORK-1"),
            tr_type=self._get("tr_type", lambda: _TR_TYPES[0]),
            cos=self._get("cos", lambda: "Gold"),
            ota_region=self._get("ota_region", lambda: _OTA_REGIONS[0]),
            roamer_count=self._get("roamer_count", lambda: RandomData.random_int(10, 500)),
            data_usage_mb=self._get("data_usage_mb", lambda: RandomData.random_int(100, 9000)),
            leakage_flag=self._get("leakage_flag", lambda: 0),
            anti_sor_flag=self._get("anti_sor_flag", lambda: 0),
            status=self._get("status", lambda: "ACTIVE"),
            modified_by=self._get("modified_by", lambda: "Admin"),
            modified_date=self._get("modified_date", lambda: now),
        )
