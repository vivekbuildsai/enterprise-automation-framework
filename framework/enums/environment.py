from enum import StrEnum


class Environment(StrEnum):
    DEV = "dev"
    QA = "qa"
    UAT = "uat"
    PREPROD = "preprod"
    PRODUCTION = "production"
