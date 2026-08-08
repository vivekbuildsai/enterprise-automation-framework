from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import DateUtils


class AuditLogSearchCriteria(BaseModel):
    user: str = ""
    date_from: str = ""
    date_to: str = ""


class AuditLogTestDataBuilder:
    @staticmethod
    def last_7_days_for_user(user: str) -> AuditLogSearchCriteria:
        return AuditLogSearchCriteria(
            user=user,
            date_from=DateUtils.format_date(DateUtils.days_from_today(-7)),
            date_to=DateUtils.format_date(DateUtils.today()),
        )
