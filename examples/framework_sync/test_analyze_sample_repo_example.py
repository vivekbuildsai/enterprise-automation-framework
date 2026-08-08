"""Example C — Existing Framework Sync (Mode 1: analyze, Mode 2: scaffold).

Demonstrates:

    sample existing framework (examples/framework_sync/sample_legacy_repo/)
          |
    RepositoryAnalyzer.analyze()   (read-only, static analysis)
          |
    compute_compatibility_report() (a real, explainable ratio — not fabricated)
          |
    generate_migration_worksheet() (a human-readable plan, never source code)

`sample_legacy_repo/` is small, sanitized fixture data written for this
example — a Selenium+pytest Page Object, not a real customer repository.

Run:
    poetry run pytest examples/framework_sync -v
"""

from __future__ import annotations

from pathlib import Path

import allure

from framework.sync import (
    RepositoryAnalyzer,
    SupportLevel,
    compute_compatibility_report,
    generate_migration_worksheet,
)

_SAMPLE_REPO = Path(__file__).parent / "sample_legacy_repo"


@allure.feature("Example: Framework Sync")
@allure.story("Analyze a sample existing repository and generate a migration worksheet")
def test_analyze_and_scaffold_a_sample_legacy_repo(tmp_path: Path) -> None:
    with allure.step("Mode 1 — read-only analysis of the sample repository"):
        analysis = RepositoryAnalyzer().analyze(_SAMPLE_REPO, source=str(_SAMPLE_REPO))

    with allure.step("Verify the analysis is real, not fabricated"):
        assert analysis.primary_language == "Python"
        detected_names = {f.name for f in analysis.detected_frameworks}
        assert "Selenium" in detected_names
        assert "pytest" in detected_names
        selenium = next(f for f in analysis.detected_frameworks if f.name == "Selenium")
        assert selenium.support_level == SupportLevel.PARTIALLY_SUPPORTED
        assert any("login_page.py" in path for path in selenium.evidence)

    with allure.step("Compute the compatibility report (a real ratio, not a fabricated score)"):
        report = compute_compatibility_report(analysis)
        allure.attach(
            report.summary,
            name="Compatibility summary",
            attachment_type=allure.attachment_type.TEXT,
        )
        assert report.total_detected == 2
        assert (
            report.compatibility_ratio == 0.5
        )  # pytest is "supported", Selenium is "partially_supported"

    with allure.step("Mode 2 — generate a migration worksheet (never source code)"):
        worksheet = generate_migration_worksheet(analysis)
        (tmp_path / "MIGRATION_WORKSHEET.md").write_text(worksheet, encoding="utf-8")
        allure.attach(
            worksheet, name="Migration worksheet", attachment_type=allure.attachment_type.TEXT
        )

        assert "Selenium" in worksheet
        assert "pytest" in worksheet
        assert "GENERATED, REVIEW BEFORE ACTING" in worksheet
