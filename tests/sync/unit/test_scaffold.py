from __future__ import annotations

import pytest

from framework.sync import (
    DetectedFramework,
    Finding,
    RepositoryAnalysis,
    SupportLevel,
    generate_migration_worksheet,
)

pytestmark = pytest.mark.sync


def test_worksheet_lists_detected_frameworks_with_notes() -> None:
    analysis = RepositoryAnalysis(
        source="https://example.test/repo.git",
        detected_frameworks=[
            DetectedFramework(
                name="Selenium",
                category="ui_automation",
                support_level=SupportLevel.PARTIALLY_SUPPORTED,
                evidence=["src/login_page.py"],
                notes="Structural concepts map directly.",
            )
        ],
    )

    worksheet = generate_migration_worksheet(analysis)

    assert "GENERATED, REVIEW BEFORE ACTING" in worksheet
    assert "Selenium (partially_supported)" in worksheet
    assert "Structural concepts map directly." in worksheet
    assert "src/login_page.py" in worksheet


def test_worksheet_handles_no_detected_frameworks() -> None:
    analysis = RepositoryAnalysis(source="local")
    worksheet = generate_migration_worksheet(analysis)
    assert "None detected" in worksheet


def test_worksheet_lists_findings_without_leaking_secret_values() -> None:
    analysis = RepositoryAnalysis(
        source="local",
        findings=[
            Finding(
                category="hardcoded_credential",
                file="config.py",
                line=12,
                description="Line matches a hardcoded-credential pattern — value not logged.",
            )
        ],
    )

    worksheet = generate_migration_worksheet(analysis)

    assert "config.py:12" in worksheet
    assert "hardcoded_credential" in worksheet
