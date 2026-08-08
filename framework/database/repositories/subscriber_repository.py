from __future__ import annotations

from dataclasses import asdict

from framework.database.models import Subscriber
from framework.database.queries import SubscriberQueries
from framework.database.repositories.base_repository import BaseRepository


class SubscriberRepository(BaseRepository[Subscriber]):
    model = Subscriber

    def create(self, subscriber: Subscriber) -> None:
        self._executor.execute_write(SubscriberQueries.INSERT, asdict(subscriber))

    def get_by_id(self, subscriber_id: str) -> Subscriber:
        row = self._executor.fetch_one(
            SubscriberQueries.FIND_BY_ID, {"subscriber_id": subscriber_id}
        )
        return self.require_one(row, not_found_message=f"Subscriber '{subscriber_id}' not found")

    def find_by_msisdn(self, msisdn: str) -> Subscriber | None:
        row = self._executor.fetch_one(SubscriberQueries.FIND_BY_MSISDN, {"msisdn": msisdn})
        return self._map_one(row)

    def find_by_tenant(self, tenant_id: str) -> list[Subscriber]:
        rows = self._executor.fetch_all(SubscriberQueries.FIND_BY_TENANT, {"tenant_id": tenant_id})
        return self._map_many(rows)

    def find_by_status(self, status: str) -> list[Subscriber]:
        rows = self._executor.fetch_all(SubscriberQueries.FIND_BY_STATUS, {"status": status})
        return self._map_many(rows)

    def find_all(self) -> list[Subscriber]:
        return self._map_many(self._executor.fetch_all(SubscriberQueries.FIND_ALL))

    def update_status(self, subscriber_id: str, status: str, *, updated_at: str) -> int:
        return self._executor.execute_write(
            SubscriberQueries.UPDATE_STATUS,
            {"subscriber_id": subscriber_id, "status": status, "updated_at": updated_at},
        )

    def delete(self, subscriber_id: str) -> int:
        return self._executor.execute_write(
            SubscriberQueries.DELETE_BY_ID, {"subscriber_id": subscriber_id}
        )

    def count(self) -> int:
        row = self._executor.fetch_one(SubscriberQueries.COUNT_ALL)
        return int(row["c"]) if row else 0

    def count_by_status(self, status: str) -> int:
        row = self._executor.fetch_one(SubscriberQueries.COUNT_BY_STATUS, {"status": status})
        return int(row["c"]) if row else 0
