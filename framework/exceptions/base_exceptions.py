class AutomationFrameworkError(Exception):
    """Base class for every exception raised by this automation framework."""


class ConfigurationError(AutomationFrameworkError):
    """Raised when configuration is missing, invalid, or fails validation."""


class ElementNotFoundError(AutomationFrameworkError):
    """Raised when a UI element cannot be located within the configured timeout."""


class ElementNotInteractableError(AutomationFrameworkError):
    """Raised when a located element cannot be interacted with (disabled, hidden, covered)."""


class DriverInitializationError(AutomationFrameworkError):
    """Raised when a browser/driver session fails to initialize."""


class ApiRequestError(AutomationFrameworkError):
    """Raised when an API call fails or returns an unexpected status/schema."""


class DatabaseConnectionError(AutomationFrameworkError):
    """Raised when a database connection cannot be established."""


class DatabaseQueryError(AutomationFrameworkError):
    """Raised when a database query fails or returns unexpected results."""


class ValidationError(AutomationFrameworkError):
    """Raised when a cross-layer (UI/API/DB) validation assertion fails."""


class TestDataError(AutomationFrameworkError):
    """Raised when test data cannot be loaded, generated, or resolved."""


class RetryExhaustedError(AutomationFrameworkError):
    """Raised when a retried operation exhausts all attempts."""


class AuthenticationError(AutomationFrameworkError):
    """Raised when a login session cannot be established, saved, or restored."""
