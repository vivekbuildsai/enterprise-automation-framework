from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import RandomData


class RoleData(BaseModel):
    name: str


class AdministrationTestDataBuilder:
    @staticmethod
    def random_role() -> RoleData:
        return RoleData(name=f"Role-{RandomData.uuid()[:8]}")
