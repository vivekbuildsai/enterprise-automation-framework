from __future__ import annotations

from typing import Any

from framework.testdata.builders import UserBuilder
from framework.testdata.builders.models import UserProfile


class UserFactory:
    @staticmethod
    def administrator(**overrides: Any) -> UserProfile:
        return UserBuilder().as_administrator().active().with_fields(**overrides).build()

    @staticmethod
    def operator(**overrides: Any) -> UserProfile:
        return UserBuilder().with_role("Operator").active().with_fields(**overrides).build()
