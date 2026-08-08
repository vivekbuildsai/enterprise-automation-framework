from __future__ import annotations

from collections.abc import Callable

from framework.enums import ValidationMode
from framework.logger import get_logger

_logger = get_logger("ValidationFacade")


class ValidationFacade:
    """Dispatches "should this validation actually run" purely from
    `ValidationMode` (`validation_mode` in `config/environments/<env>.yaml`
    / `AUTOMATION_VALIDATION_MODE`) — UI-only, UI+API, UI+DB, or UI+API+DB. Test
    code calls the same methods in every mode; the facade decides whether
    the API/DB callable it was handed actually executes.

    This is the seam the milestone brief describes::

        login_page.login(user)
        dashboard.verify_dashboard()                                     # UI — always runs
        facade.verify_api(lambda: api_validator.verify_dashboard(user))  # iff mode includes API
        facade.verify_database(lambda: db_validator.verify_dashboard(user))  # iff mode includes DB

    Switching `ui_only` -> `ui_api_database` in YAML makes every existing
    `verify_api`/`verify_database` call start executing — no test file
    changes. A callable (not the result of calling it) is passed in
    specifically so a disabled layer costs nothing: an API call or DB query
    behind a skipped lambda never happens.
    """

    def __init__(self, mode: ValidationMode) -> None:
        self._mode = mode

    @property
    def mode(self) -> ValidationMode:
        return self._mode

    @property
    def ui_enabled(self) -> bool:
        return True  # every `ValidationMode` includes UI

    @property
    def api_enabled(self) -> bool:
        return self._mode in (ValidationMode.UI_API, ValidationMode.UI_API_DATABASE)

    @property
    def database_enabled(self) -> bool:
        return self._mode in (ValidationMode.UI_DATABASE, ValidationMode.UI_API_DATABASE)

    def verify_ui(self, check: Callable[[], None]) -> None:
        """UI validation always runs — included for symmetry with
        `verify_api`/`verify_database` so callers can treat all three
        uniformly (e.g. in `run()`).
        """
        check()

    def verify_api(self, check: Callable[[], None]) -> None:
        if self.api_enabled:
            check()
        else:
            _logger.debug(f"Skipped API validation (validation_mode={self._mode.value})")

    def verify_database(self, check: Callable[[], None]) -> None:
        if self.database_enabled:
            check()
        else:
            _logger.debug(f"Skipped database validation (validation_mode={self._mode.value})")

    def run(
        self,
        *,
        ui: Callable[[], None] | None = None,
        api: Callable[[], None] | None = None,
        database: Callable[[], None] | None = None,
    ) -> None:
        """Single-call convenience combining all three — the exact shape of
        the milestone brief's example, as one call instead of three::

            facade.run(
                ui=dashboard.verify_dashboard,
                api=lambda: api_validator.verify_dashboard(user),
                database=lambda: db_validator.verify_dashboard(user),
            )
        """
        if ui is not None:
            self.verify_ui(ui)
        if api is not None:
            self.verify_api(api)
        if database is not None:
            self.verify_database(database)
