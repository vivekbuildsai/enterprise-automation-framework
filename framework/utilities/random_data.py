from __future__ import annotations

from datetime import date, datetime

from faker import Faker

_faker = Faker()


class RandomData:
    """Thin wrapper over Faker so test-data builders share one seeded
    instance and one import (`from framework.utilities import RandomData`)
    instead of every module reaching for `faker` directly with its own
    `Faker()` instance.
    """

    @staticmethod
    def full_name() -> str:
        return _faker.name()

    @staticmethod
    def email() -> str:
        return _faker.email()

    @staticmethod
    def phone_number() -> str:
        return _faker.phone_number()

    @staticmethod
    def username() -> str:
        return _faker.user_name()

    @staticmethod
    def password(length: int = 12) -> str:
        return _faker.password(length=length)

    @staticmethod
    def uuid() -> str:
        return str(_faker.uuid4())

    @staticmethod
    def company_name() -> str:
        return _faker.company()

    @staticmethod
    def sentence() -> str:
        return _faker.sentence()

    @staticmethod
    def random_int(min_value: int = 0, max_value: int = 1000) -> int:
        return _faker.random_int(min=min_value, max=max_value)

    @staticmethod
    def street_address() -> str:
        return _faker.street_address()

    @staticmethod
    def city() -> str:
        return _faker.city()

    @staticmethod
    def postcode() -> str:
        return _faker.postcode()

    @staticmethod
    def country() -> str:
        return _faker.country()

    @staticmethod
    def country_code() -> str:
        return _faker.country_code()

    @staticmethod
    def full_address() -> str:
        return _faker.address().replace("\n", ", ")

    @staticmethod
    def date_of_birth(*, minimum_age: int = 18, maximum_age: int = 90) -> date:
        return _faker.date_of_birth(minimum_age=minimum_age, maximum_age=maximum_age)

    @staticmethod
    def date_between(*, start: str = "-30d", end: str = "today") -> date:
        return _faker.date_between(start_date=start, end_date=end)

    @staticmethod
    def datetime_between(*, start: str = "-30d", end: str = "now") -> datetime:
        return _faker.date_time_between(start_date=start, end_date=end)

    @staticmethod
    def future_datetime(*, end: str = "+30d") -> datetime:
        return _faker.date_time_between(start_date="now", end_date=end)
