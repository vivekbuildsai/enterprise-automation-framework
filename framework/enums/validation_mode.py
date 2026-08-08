from enum import StrEnum


class ValidationMode(StrEnum):
    """Controls which validation layers a test exercises.

    Selected purely via config (`AUTOMATION_VALIDATION_MODE` / environment YAML).
    Test code calls `context.validate(...)` regardless of mode — the mode
    only changes which repositories/clients the ValidationFacade wires up,
    so switching modes never requires touching test code.
    """

    UI_ONLY = "ui_only"
    UI_API = "ui_api"
    UI_DATABASE = "ui_database"
    UI_API_DATABASE = "ui_api_database"
