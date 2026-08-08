"""CLI-level coverage for the new inventory/scope capabilities —
`python -m framework.sync analyze` prints the "EXISTING AUTOMATION
INVENTORY" block, and `scaffold --scope/--selector` implements Mode B
("Selective Migration") end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from framework.sync.__main__ import main

pytestmark = pytest.mark.sync

_FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_analyze_prints_existing_automation_inventory(tmp_path: Path, capsys) -> None:
    report_path = tmp_path / "analysis.json"
    exit_code = main(
        ["analyze", str(_FIXTURES / "java_selenium_testng"), "--report", str(report_path)]
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "EXISTING AUTOMATION INVENTORY" in out
    assert "Tests Detected:" in out
    assert "Test Runner:" in out


def test_scaffold_default_scope_covers_every_test(tmp_path: Path) -> None:
    report_path = tmp_path / "analysis.json"
    output_dir = tmp_path / "generated"
    main(["analyze", str(_FIXTURES / "java_selenium_testng"), "--report", str(report_path)])

    exit_code = main(["scaffold", "--report", str(report_path), "--output-dir", str(output_dir)])

    assert exit_code == 0
    worksheet = (output_dir / "MIGRATION_WORKSHEET.md").read_text(encoding="utf-8")
    assert "Migration candidates (scope: repository)" in worksheet
    assert "validLoginReachesSecureArea" in worksheet
    assert "dashboardShowsWelcomeMessage" in worksheet


def test_scaffold_scoped_to_one_tag_lists_only_that_test(tmp_path: Path) -> None:
    report_path = tmp_path / "analysis.json"
    output_dir = tmp_path / "generated"
    main(["analyze", str(_FIXTURES / "java_selenium_testng"), "--report", str(report_path)])

    exit_code = main(
        [
            "scaffold",
            "--report",
            str(report_path),
            "--output-dir",
            str(output_dir),
            "--scope",
            "tag",
            "--selector",
            "smoke",
        ]
    )

    assert exit_code == 0
    worksheet = (output_dir / "MIGRATION_WORKSHEET.md").read_text(encoding="utf-8")
    assert "validLoginReachesSecureArea" in worksheet
    assert "dashboardShowsWelcomeMessage" not in worksheet
    assert "invalidPasswordShowsError" not in worksheet


def test_scaffold_non_repository_scope_without_selector_fails_cleanly(
    tmp_path: Path, capsys
) -> None:
    report_path = tmp_path / "analysis.json"
    output_dir = tmp_path / "generated"
    main(["analyze", str(_FIXTURES / "java_selenium_testng"), "--report", str(report_path)])

    exit_code = main(
        [
            "scaffold",
            "--report",
            str(report_path),
            "--output-dir",
            str(output_dir),
            "--scope",
            "tag",
        ]
    )

    assert exit_code == 1
    assert "--selector" in capsys.readouterr().err


def test_scaffold_invalid_scope_value_is_rejected_by_argparse() -> None:
    with pytest.raises(SystemExit):
        main(["scaffold", "--scope", "not-a-real-scope"])
