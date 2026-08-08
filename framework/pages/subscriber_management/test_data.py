from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import RandomData


class SubscriberData(BaseModel):
    first_name: str
    last_name: str
    email: str


class SubscriberTestDataBuilder:
    """Dynamic builder for subscriber test data — for a future create/update
    flow once the real app supports it. Static/fixed data (known search
    terms, expected columns) lives in `data/testdata/subscriber_management/`
    instead, loaded via `TestDataLoader` — this builder is only for
    "generate me a plausible new subscriber" cases.
    """

    @staticmethod
    def random_subscriber() -> SubscriberData:
        return SubscriberData(
            first_name=RandomData.full_name().split()[0],
            last_name=RandomData.full_name().split()[-1],
            email=RandomData.email(),
        )
