from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import RandomData


class NewUserData(BaseModel):
    username: str
    email: str
    role: str


class UserManagementTestDataBuilder:
    @staticmethod
    def random_user(*, role: str = "Viewer") -> NewUserData:
        return NewUserData(username=RandomData.username(), email=RandomData.email(), role=role)
