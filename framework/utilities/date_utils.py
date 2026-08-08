from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


class DateUtils:
    """Date helpers for test data — timezone-aware (UTC) throughout to avoid
    the classic "works on my machine, fails in CI" local-timezone bug.
    """

    @staticmethod
    def today() -> date:
        return datetime.now(UTC).date()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def format_date(value: date, fmt: str = "%Y-%m-%d") -> str:
        return value.strftime(fmt)

    @staticmethod
    def days_from_today(offset_days: int) -> date:
        """Positive `offset_days` -> future date, negative -> past date —
        the common need for "expiry in 30 days" / "created 7 days ago" test
        data without every test doing its own `timedelta` arithmetic.
        """
        return DateUtils.today() + timedelta(days=offset_days)
