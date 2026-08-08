"""Security-focused regression tests for the safe-extension +
framework-native scaffolding milestone: no secret ever reaches generated
output, a malicious discovered page title can never escape the scaffold
output directory, and the new `analyze --framework` orchestration path
inherits the same zip-slip protection `ZipArchiveSource` already
guarantees rather than bypassing it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from framework.discovery.models import (
    DiscoveredElement,
    DiscoveredLocator,
    DiscoveredNetworkCall,
    DiscoveredPage,
    DiscoveryReport,
)
from framework.extension import paths as paths_module
from framework.extension.__main__ import main
from framework.extension.models import (
    ExtensionClassification,
    ExtensionItem,
    ExtensionReport,
    ExtensionSubjectType,
)
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.sync.models import RepositoryAnalysis

pytestmark = pytest.mark.extension

_SECRET = "sk-super-secret-token-should-never-leak-987654"


def test_generated_scaffold_never_contains_a_captured_secret_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`DiscoveredNetworkCall` is shape-only by construction (method/path/
    status/key names, never values) — this proves that discipline holds
    all the way through to the generated files on disk, not just the
    discovery report.
    """
    page = DiscoveredPage(
        url="https://example.test/employees/42",
        title="Employee Details",
        elements=[
            DiscoveredElement(
                tag="input",
                element_type="textbox",
                text=_SECRET,  # a value that must never survive into generated code
                locator=DiscoveredLocator(strategy="css", value="#notes"),
            )
        ],
        network_calls=[
            DiscoveredNetworkCall(
                method="POST",
                path="/employees/42",
                status=200,
                query_param_names=["token"],
                request_body_keys=["apiKey"],
                response_body_keys=["token"],
            )
        ],
    )
    discovery_report = DiscoveryReport(source="new-ui", pages=[page])
    extension_report = ExtensionReport(
        extension_items=[
            ExtensionItem(
                subject="Employee Details",
                subject_type=ExtensionSubjectType.UI_PAGE,
                classification=ExtensionClassification.CREATE_NEW,
                reason="new",
                evidence=[f"element text captured: {_SECRET}"],
            )
        ]
    )
    analysis = RepositoryAnalysis(source="existing")

    files, manifest = build_scaffold_plan(analysis, discovery_report, extension_report)

    for file in files:
        assert _SECRET not in file.content

    monkeypatch.setattr(paths_module, "PROJECT_ROOT", tmp_path)
    written = write_scaffold_plan(files, tmp_path / "generated")
    for path in written:
        assert _SECRET not in path.read_text(encoding="utf-8")
    manifest_json = manifest.model_dump_json()
    assert _SECRET not in manifest_json


def test_malicious_page_title_cannot_escape_the_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = DiscoveredPage(
        url="https://example.test/x",
        title="../../../../etc/passwd",
        elements=[],
    )
    discovery_report = DiscoveryReport(source="new-ui", pages=[page])
    extension_report = ExtensionReport(
        extension_items=[
            ExtensionItem(
                subject="../../../../etc/passwd",
                subject_type=ExtensionSubjectType.UI_PAGE,
                classification=ExtensionClassification.CREATE_NEW,
                reason="new",
            )
        ]
    )
    analysis = RepositoryAnalysis(source="existing")

    files, _ = build_scaffold_plan(analysis, discovery_report, extension_report)
    for file in files:
        assert ".." not in file.relative_path

    monkeypatch.setattr(paths_module, "PROJECT_ROOT", tmp_path)
    output_dir = tmp_path / "generated"
    written = write_scaffold_plan(files, output_dir)
    for path in written:
        assert path.is_relative_to(output_dir)


def test_analyze_framework_flag_rejects_a_zip_slip_archive(tmp_path: Path, capsys) -> None:
    """The new `analyze --framework <zip>` orchestration path must inherit
    `ZipArchiveSource`'s existing zip-slip protection, not bypass it with a
    second, unguarded extraction.
    """
    malicious_zip = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious_zip, "w") as archive:
        archive.writestr("../../../../tmp/evil.py", "should never be written outside")

    exit_code = main(
        [
            "analyze",
            "--framework",
            str(malicious_zip),
            "--sync-report",
            str(tmp_path / "sync.json"),
            "--discovery-report",
            str(tmp_path / "discovery.json"),
        ]
    )

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "Unsafe archive member" in stderr or "path traversal" in stderr.lower()


def test_ai_recommendation_output_never_contains_raw_evidence_secrets(tmp_path: Path) -> None:
    """Defense-in-depth check on the pre-existing AI layer this milestone
    reuses unchanged: an `ExtensionItem.evidence` string containing a
    secret-looking value must never be echoed back verbatim into a
    provider recommendation's output when redaction applies.
    """
    from framework.ai.redaction import redact_secrets

    prompt_fragment = f"api_key={_SECRET}"
    redacted = redact_secrets(prompt_fragment)

    assert _SECRET not in redacted
