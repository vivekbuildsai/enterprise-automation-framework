from __future__ import annotations

from framework.database.models import Network
from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.utilities.id_sequence import sequences
from framework.utilities.random_data import RandomData

_network_sequence = sequences.get("network")

_OTA_REGIONS = ("EMEA", "EU", "APAC", "AMER")


class NetworkBuilder(BaseBuilder[Network]):
    """Fluent builder for `framework.database.models.Network`."""

    def with_network_id(self, network_id: str) -> NetworkBuilder:
        return self._set(network_id=network_id)

    def with_network_code(self, network_code: str) -> NetworkBuilder:
        return self._set(network_code=network_code)

    def with_network_name(self, network_name: str) -> NetworkBuilder:
        return self._set(network_name=network_name)

    def with_tenant_id(self, tenant_id: str) -> NetworkBuilder:
        return self._set(tenant_id=tenant_id)

    def with_ota_region(self, ota_region: str) -> NetworkBuilder:
        return self._set(ota_region=ota_region)

    def with_status(self, status: str) -> NetworkBuilder:
        return self._set(status=status)

    def active(self) -> NetworkBuilder:
        return self.with_status("ACTIVE")

    def build(self) -> Network:
        network_code = self._get("network_code", lambda: f"N{RandomData.random_int(100, 999)}")
        return Network(
            network_id=self._get("network_id", lambda: _network_sequence.next_id(prefix="NETWORK")),
            network_code=network_code,
            network_name=self._get("network_name", lambda: f"Network {network_code}"),
            tenant_id=self._get("tenant_id", lambda: f"TENANT-{RandomData.random_int(1, 999)}"),
            ota_region=self._get("ota_region", lambda: _OTA_REGIONS[RandomData.random_int(0, 3)]),
            status=self._get("status", lambda: "ACTIVE"),
        )
