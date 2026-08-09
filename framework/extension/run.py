"""`extension run` — the single-command orchestrator for the full
extension-analysis pipeline, in the order the governing philosophy
requires:

    ANALYZE FIRST -> CLASSIFY SECOND -> CORRELATE THIRD -> REVIEW FOURTH -> SCAFFOLD LAST

Never: DISCOVER -> BLINDLY GENERATE CODE.

This module is thin orchestration only. Every actual stage already has
its own module; `run()` below calls into them in sequence and never
reimplements environment detection (`framework.doctor`), repository
analysis (`framework.sync`), UI discovery (`framework.discovery`),
network classification (`framework.extension.network_classification`),
login-page/quality detection (`framework.extension.auth_detection`/
`discovery_quality`), correlation (`framework.extension.correlation`), or
gap analysis (`framework.extension.gap_analysis`). The report/discover
loading logic is the exact same private helpers
`framework.extension.__main__ analyze` already uses (`_load_or_analyze_framework`,
`_discover_or_load_new_ui`, `_filter_pages_to_kept_calls`) — imported and
reused here, not copied, so the two entry points can never drift apart.

Stages:
  1. preflight    `framework.doctor` capability check        (skip: --skip-doctor)
  2. analyze      existing framework capability catalog      (`framework.sync`)
  3. discover     new UI discovery + network capture         (`framework.discovery`)
  4. classify     network classification/deduplication       (`network_classification`)
  5. quality      login-page detection + quality score        (`discovery_quality`)
  6. correlate    UI/API/DB correlation against the catalog   (`framework.extension.correlation`)
  7. plan         extension gap report + test opportunities   (`framework.extension.gap_analysis`)
  8. safety-gate  refuses BLOCKED discovery quality, or (with --scaffold) a dirty git
                  tree without --allow-dirty
  9. scaffold     optional, only with --scaffold and (--yes or an interactive y/N
                  confirmation)
 10. report       final summary + exit code

Every artifact lands under `<--output-dir>/<UTC timestamp>/` — nothing is
scattered across the repository root.

Exit codes (documented here and matched by `framework.doctor.__main__`'s
own exit code 3, so CI can treat 3 uniformly as "environment problem"
from either entry point):

  0  success — analysis complete (and scaffold written, if requested and approved)
  1  unexpected/unhandled error (see `framework.cli_common.run_command`)
  2  usage error — argparse's own default for invalid CLI arguments
  3  environment preflight failed (`framework.doctor`)
  4  discovery quality is BLOCKED — the run stops here; no scaffold, and
     no claim is made that the report reflects the real application
  5  git working tree is dirty and --allow-dirty was not passed (only
     checked when --scaffold is requested)
  6  --scaffold was requested but declined: --dry-run, or no --yes and
     the user answered anything other than "y" (or stdin is not
     interactive, where a missing --yes is always treated as declined
     rather than hanging)
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from framework.discovery.models import DiscoveryReport
from framework.doctor.detectors import detect_all, detect_git
from framework.doctor.models import DoctorReport
from framework.doctor.report import (
    apply_not_required_downgrades,
    format_summary_line,
    recommend_browser,
)
from framework.extension.__main__ import (
    _all_network_calls,
    _discover_or_load_new_ui,
    _filter_pages_to_kept_calls,
    _load_or_analyze_framework,
)
from framework.extension.correlation import correlate_database_usage, correlate_network_calls
from framework.extension.discovery_quality import compute_discovery_quality
from framework.extension.gap_analysis import (
    build_extension_items,
    build_test_opportunities,
    format_reuse_matrix,
)
from framework.extension.models import DiscoveryQualityLevel, ExtensionReport, ScaffoldTarget
from framework.extension.network_classification import classify_network_calls, page_host_from_url
from framework.extension.paths import resolve_scaffold_output_dir
from framework.extension.scaffold import build_scaffold_plan, write_scaffold_plan
from framework.sync.models import RepositoryAnalysis

EXIT_OK = 0
EXIT_ENVIRONMENT_FAILURE = 3
EXIT_DISCOVERY_BLOCKED = 4
EXIT_GIT_DIRTY = 5
EXIT_SCAFFOLD_DECLINED = 6


def _timestamped_output_dir(output_dir: str) -> Path:
    root = resolve_scaffold_output_dir(output_dir)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _run_preflight(*, skip: bool) -> int | None:
    """Returns an exit code to stop on, or `None` to continue. Reuses
    `framework.doctor`'s own detection + browser-recommendation + summary
    formatting wholesale — this never re-implements capability detection.
    """
    if skip:
        print("Preflight: skipped (--skip-doctor).")
        return None
    capabilities = detect_all(ffmpeg_required=False)
    browser, reason = recommend_browser(capabilities, requested=None)
    capabilities = apply_not_required_downgrades(capabilities, selected_browser=browser)
    report = DoctorReport(
        capabilities=capabilities, recommended_browser=browser, recommendation_reason=reason
    )
    print(format_summary_line(report))
    if not report.passed:
        print("Run `python -m framework doctor` for the full capability matrix.")
        return EXIT_ENVIRONMENT_FAILURE
    return None


def _check_git_dirty(*, allow_dirty: bool) -> int | None:
    """Returns an exit code to stop on, or `None` to continue. Reuses
    `framework.doctor.detectors.detect_git`'s own dirty-tree detection —
    its `Working Tree` capability's `remediation` already says "pass
    --allow-dirty", which is exactly what this gate honors.
    """
    working_tree = next((c for c in detect_git() if c.name == "Working Tree"), None)
    if working_tree is None or working_tree.available:
        return None
    print(f"\nGit working tree check: {working_tree.reason}")
    if allow_dirty:
        print("Continuing anyway (--allow-dirty).")
        return None
    print(f"Refusing to scaffold into a dirty working tree. {working_tree.remediation}")
    return EXIT_GIT_DIRTY


def _confirm_scaffold_write(*, file_count: int, destination: Path, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("\n--yes was not given and stdin is not interactive — declining to avoid hanging.")
        return False
    answer = input(f"\nWrite {file_count} file(s) under {destination}? [y/N] ").strip().lower()
    return answer == "y"


def _run_analysis_stages(
    args: argparse.Namespace, output_dir: Path
) -> tuple[RepositoryAnalysis, DiscoveryReport, ExtensionReport]:
    """Stages 2-7: analyze -> discover -> classify -> quality -> correlate
    -> plan. Returns the raw analysis/discovery reports (the scaffold
    stage needs both) plus the assembled `ExtensionReport`, already saved
    to `output_dir / "extension_report.json"`.
    """
    stage_args = argparse.Namespace(**vars(args))
    stage_args.sync_report = str(output_dir / "existing_framework_analysis.json")
    stage_args.discovery_report = str(output_dir / "new_ui_discovery_report.json")

    analysis = _load_or_analyze_framework(stage_args)
    discovery_report = _discover_or_load_new_ui(stage_args)
    catalog = analysis.capability_catalog

    calls = _all_network_calls(discovery_report)
    page_host = page_host_from_url(discovery_report.pages[0].url) if discovery_report.pages else ""
    classification = classify_network_calls(calls, page_host=page_host)
    quality = compute_discovery_quality(
        discovery_report.pages, requested_url=args.url, classification=classification
    )
    application_calls = classification.application_and_auth_calls()

    correlations = correlate_network_calls(application_calls, catalog) + correlate_database_usage(
        application_calls, catalog
    )
    filtered_pages = _filter_pages_to_kept_calls(discovery_report.pages, application_calls)
    extension_items = build_extension_items(filtered_pages, catalog)
    test_opportunities = build_test_opportunities(filtered_pages, catalog)

    report = ExtensionReport(
        existing_framework_source=analysis.source,
        new_ui_source=discovery_report.source,
        correlations=correlations,
        extension_items=extension_items,
        test_opportunities=test_opportunities,
        network_classification=classification,
        discovery_quality=quality,
    )
    report.save(output_dir / "extension_report.json")

    summary = classification.summary
    print(
        f"\nNetwork classification: {summary.raw_count} raw call(s) -> "
        f"{summary.application_candidate_count} application API, "
        f"{summary.authentication_count} authentication, "
        f"{summary.static_or_framework_ignored} static/framework, "
        f"{summary.analytics_ignored} analytics, {summary.third_party_ignored} third-party, "
        f"{summary.document_ignored} document, {summary.unknown_count} unknown."
    )
    print(f"Discovery quality: {quality.level.value.upper()} ({quality.score}/100)")
    for reason in quality.reasons:
        print(f"  - {reason}")
    print(f"\n{len(extension_items)} extension item(s):")
    print(format_reuse_matrix(extension_items))
    print(f"\nFull extension report: {output_dir / 'extension_report.json'}")
    return analysis, discovery_report, report


def _run_scaffold_stage(
    args: argparse.Namespace,
    analysis: RepositoryAnalysis,
    discovery_report: DiscoveryReport,
    report: ExtensionReport,
    output_dir: Path,
) -> int:
    """Stages 8-9: safety-gate (dirty git tree) -> scaffold plan -> write
    (only after --dry-run is ruled out and the write is confirmed).
    """
    git_exit = _check_git_dirty(allow_dirty=args.allow_dirty)
    if git_exit is not None:
        return git_exit

    target = ScaffoldTarget(args.target) if args.target else None
    files, manifest = build_scaffold_plan(analysis, discovery_report, report, target=target)
    scaffold_dir = output_dir / "scaffold"
    print(f"\nScaffold target: {manifest.target.value}")
    print(f"{len(files)} file(s) in the plan:")
    for file in files:
        print(f"  {file.relative_path}")

    if args.dry_run:
        write_scaffold_plan(files, scaffold_dir, overwrite=args.overwrite, dry_run=True)
        print(f"\n--dry-run: no files written (would write under {scaffold_dir}).")
        return EXIT_OK

    if not _confirm_scaffold_write(
        file_count=len(files), destination=scaffold_dir, assume_yes=args.yes
    ):
        print("Declined — nothing written.")
        return EXIT_SCAFFOLD_DECLINED

    written = write_scaffold_plan(files, scaffold_dir, overwrite=args.overwrite)
    manifest_path = scaffold_dir / "extension-manifest.json"
    manifest.save(manifest_path)
    print(f"\n{len(written)} file(s) written under {scaffold_dir}.")
    print(f"Manifest: {manifest_path}")
    print(
        "GENERATED SCAFFOLD — REVIEW REQUIRED. Review every TODO and run the customer's "
        "normal test command before treating any of this as real automation."
    )
    return EXIT_OK


def run(args: argparse.Namespace) -> int:
    preflight_exit = _run_preflight(skip=args.skip_doctor)
    if preflight_exit is not None:
        return preflight_exit

    output_dir = _timestamped_output_dir(args.output_dir)
    print(f"\nOutput directory: {output_dir}")

    analysis, discovery_report, report = _run_analysis_stages(args, output_dir)

    if report.discovery_quality and report.discovery_quality.level == DiscoveryQualityLevel.BLOCKED:
        print(
            "\nSAFETY GATE: discovery quality is BLOCKED — this looks like an authentication "
            "redirect rather than the real application. Refusing to continue; re-run with a "
            "valid authenticated session before scaffolding from this report."
        )
        return EXIT_DISCOVERY_BLOCKED

    if not args.scaffold:
        print("\n--scaffold not requested — analysis complete, nothing written.")
        return EXIT_OK

    return _run_scaffold_stage(args, analysis, discovery_report, report, output_dir)
