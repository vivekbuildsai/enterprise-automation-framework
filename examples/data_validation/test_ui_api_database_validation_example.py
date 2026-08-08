"""Example F — UI + API + Database validation (the framework's key
differentiator, end to end).

Demonstrates the full pipeline used by `framework.hybrid.ValidationFacade`:

    UI (what a user sees)
          |
    API (what the backend returns)          <- framework.api.client.ApiClient
          |
    Database (what's actually stored)        <- framework.database.utilities.QueryExecutor
          |
    Normalization                            <- aligning both sides on the same field names
          |
    Tolerance-aware comparison                <- DataComparator + Tolerance
          |
    Validation result                         <- ComparisonResult.to_report()

`ValidationFacade(mode)` decides which of `verify_api`/`verify_database`
actually execute, purely from one config value
(`validation_mode` in `config/environments/*.yaml`) — this example calls
`facade.run(ui=..., api=..., database=...)` exactly once; nothing about
the test body changes if `validation_mode` is later switched to
`ui_only`/`ui_api`/`ui_database` — only which callables actually run does.

REAL vs LOCAL, stated plainly:
    UI       — LOCAL: a static page standing in for a real dashboard (no
               public demo site displays this exact API's data).
    API      — REAL: a live GET to https://dummyjson.com/users/1 (a public
               fake-data API used elsewhere in this framework's own test
               suite — no account or API key needed).
    Database — LOCAL: SQLite in-memory, seeded by this example itself to
               simulate "what's stored" — no external database required.

No customer-specific or internal domain models are used — every value is
a plain dict, exactly like `examples/data_validation/
test_widget_vs_database_example.py` (Example B).

Run:
    poetry run pytest examples/data_validation/test_ui_api_database_validation_example.py -v
"""

from __future__ import annotations

import allure

from framework.api.client import ApiClient
from framework.config.models import DatabaseConfig, EnvironmentSettings, UiConfig
from framework.database.connection import DatabaseManager
from framework.database.utilities import DataComparator, Tolerance
from framework.database.utilities.query_executor import QueryExecutor
from framework.enums.validation_mode import ValidationMode
from framework.hybrid import ValidationFacade


@allure.feature("Example: UI + API + Database Validation")
@allure.story("A user's profile agrees across the UI, the real API, and the database")
def test_user_profile_matches_across_ui_api_and_database(page) -> None:
    # `ui_api_database` — the mode that makes every verify_api/verify_database
    # call below actually execute. Try `ValidationMode.UI_ONLY` here and rerun:
    # the exact same test body then only performs the UI check.
    facade = ValidationFacade(ValidationMode.UI_API_DATABASE)

    results: dict[str, dict[str, object]] = {}

    with allure.step("UI (LOCAL) — a page displaying a user's profile"):

        def check_ui() -> None:
            page.set_content(
                """
                <html><body>
                    <div id="first-name">Emily</div>
                    <div id="last-name">Johnson</div>
                    <div id="age">30</div>
                </body></html>
                """
            )
            results["ui"] = {
                "first_name": page.locator("#first-name").inner_text(),
                "last_name": page.locator("#last-name").inner_text(),
                "age": int(page.locator("#age").inner_text()),
            }

        facade.verify_ui(check_ui)

    with allure.step("API (REAL) — GET https://dummyjson.com/users/1"):

        def check_api() -> None:
            with ApiClient("https://dummyjson.com") as client:
                response = client.get("/users/1")
            body = response.json()
            results["api"] = {
                "first_name": body["firstName"],
                "last_name": body["lastName"],
                "age": body["age"],
            }

        facade.verify_api(check_api)

    with allure.step("Database (LOCAL) — SQLite, seeded to match the real API"):

        def check_database() -> None:
            settings = EnvironmentSettings(
                environment="dev",
                ui=UiConfig(base_url="https://example.test"),
                database={
                    "example_db": DatabaseConfig(
                        enabled=True, dialect="sqlite", database=":memory:"
                    )
                },
            )
            manager = DatabaseManager(settings)
            with manager.connection("example_db") as conn:
                executor = QueryExecutor(conn, db_key="example_db", dialect="sqlite")
                executor.execute(
                    "CREATE TABLE users (id INTEGER PRIMARY KEY, first_name TEXT, "
                    "last_name TEXT, age INTEGER)"
                )
                executor.execute(
                    "INSERT INTO users (id, first_name, last_name, age) VALUES "
                    "(1, 'Emily', 'Johnson', 29)"
                )
                conn.commit()
                row = executor.fetch_one(
                    "SELECT first_name, last_name, age FROM users WHERE id = 1"
                )
            results["database"] = dict(row)
            manager.dispose_all()

        facade.verify_database(check_database)

    with allure.step("Compare Database (source of truth) vs UI, and vs the real API"):
        db_vs_ui = DataComparator.compare(
            results["database"],
            results["ui"],
            left_label="database",
            right_label="ui",
            tolerance=Tolerance(absolute=2),  # the UI's "age" is allowed to be slightly stale
        )
        db_vs_api = DataComparator.compare(
            results["database"], results["api"], left_label="database", right_label="api"
        )
        allure.attach(
            db_vs_ui.to_report() + "\n\n" + db_vs_api.to_report(),
            name="Validation result",
            attachment_type=allure.attachment_type.TEXT,
        )

        assert db_vs_ui.matched, db_vs_ui.to_report()
        assert db_vs_api.matched, db_vs_api.to_report()

        age_comparison = next(fc for fc in db_vs_ui.field_comparisons if fc.field == "age")
        assert age_comparison.difference == 1  # UI said 30, database/API say 29 — within tolerance
