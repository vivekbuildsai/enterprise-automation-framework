from __future__ import annotations

from pydantic import BaseModel

from framework.utilities import DateUtils


class ReportRequest(BaseModel):
    report_type: str
    date_from: str
    date_to: str


class ReportTestDataBuilder:
    @staticmethod
    def last_30_days(report_type: str = "Usage Summary") -> ReportRequest:
        return ReportRequest(
            report_type=report_type,
            date_from=DateUtils.format_date(DateUtils.days_from_today(-30)),
            date_to=DateUtils.format_date(DateUtils.today()),
        )
