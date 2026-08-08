from framework.database.utilities.comparison import DataComparator


class EmployeeValidator:
    def validate(self, actual, expected):
        return DataComparator.compare(actual, expected)
