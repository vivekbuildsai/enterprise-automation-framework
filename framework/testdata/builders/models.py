from __future__ import annotations

from dataclasses import dataclass

# Entity types this milestone's builders produce that don't already have a
# `framework.database.models` equivalent (Tenant/Network/Subscriber/
# SteeringZone/Alarm builders reuse those dataclasses directly instead of
# duplicating them here).


@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: str
    username: str
    first_name: str
    last_name: str
    email: str
    password: str
    role: str
    status: str
    created_at: str

    def to_api_create_request(self) -> dict[str, object]:
        """Field mapping for `framework.api.models.user_models.
        CreateUserRequest` — kept as a plain dict (not importing the API
        layer's Pydantic model here) so `framework.testdata` never has to
        depend on `framework.api`; the caller constructs the actual
        `CreateUserRequest` from this at the call site.
        """
        return {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
        }


@dataclass(frozen=True, slots=True)
class SimCard:
    iccid: str
    imsi: str
    msisdn: str
    status: str
    subscriber_id: str
    tenant_id: str
    activation_date: str | None


@dataclass(frozen=True, slots=True)
class BillingRecord:
    billing_id: str
    subscriber_id: str
    tenant_id: str
    amount: float
    currency: str
    billing_date: str
    status: str
    description: str
