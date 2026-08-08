from __future__ import annotations

from datetime import UTC, datetime

from framework.testdata.builders.base_builder import BaseBuilder
from framework.testdata.builders.models import UserProfile
from framework.testdata.utilities.id_sequence import sequences
from framework.utilities.random_data import RandomData

_user_sequence = sequences.get("user")

_ROLES = ("Operator", "Administrator", "Analyst", "Viewer")


class UserBuilder(BaseBuilder[UserProfile]):
    """Fluent builder for `UserProfile` — a portal/operator user, distinct
    from `SubscriberBuilder` (an end-customer's telecom subscription).
    """

    def with_user_id(self, user_id: str) -> UserBuilder:
        return self._set(user_id=user_id)

    def with_username(self, username: str) -> UserBuilder:
        return self._set(username=username)

    def with_name(self, first_name: str, last_name: str) -> UserBuilder:
        return self._set(first_name=first_name, last_name=last_name)

    def with_email(self, email: str) -> UserBuilder:
        return self._set(email=email)

    def with_password(self, password: str) -> UserBuilder:
        return self._set(password=password)

    def with_role(self, role: str) -> UserBuilder:
        return self._set(role=role)

    def with_status(self, status: str) -> UserBuilder:
        return self._set(status=status)

    def as_administrator(self) -> UserBuilder:
        return self.with_role("Administrator")

    def active(self) -> UserBuilder:
        return self.with_status("ACTIVE")

    def build(self) -> UserProfile:
        first_name = self._get("first_name", lambda: RandomData.full_name().split()[0])
        last_name = self._get("last_name", lambda: RandomData.full_name().split()[-1])
        return UserProfile(
            user_id=self._get("user_id", lambda: _user_sequence.next_id(prefix="USER")),
            username=self._get("username", RandomData.username),
            first_name=first_name,
            last_name=last_name,
            email=self._get("email", RandomData.email),
            password=self._get("password", lambda: RandomData.password(length=16)),
            role=self._get("role", lambda: _ROLES[0]),
            status=self._get("status", lambda: "ACTIVE"),
            created_at=self._get("created_at", lambda: datetime.now(UTC).isoformat()),
        )
