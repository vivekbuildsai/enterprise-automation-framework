from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import RandomData


class PolicyData(BaseModel):
    name: str
    policy_type: str


class PolicyTestDataBuilder:
    @staticmethod
    def random_policy(*, policy_type: str = "Standard") -> PolicyData:
        return PolicyData(name=f"Policy-{RandomData.uuid()[:8]}", policy_type=policy_type)
