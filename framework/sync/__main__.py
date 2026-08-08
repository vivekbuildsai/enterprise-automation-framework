"""CLI for the Existing Framework Sync capability.

    poetry run python -m framework.sync analyze <source> --report analysis.json
    poetry run python -m framework.sync scaffold --report analysis.json --output-dir generated/
    poetry run python -m framework.sync diff <before.json> <after.json>
    poetry run python -m framework.sync recommend --report analysis.json --env dev \
        --output mapping_recommendations.json

`<source>` may be a local directory, a `.zip` archive, or a git URL
(anything `git clone` accepts — GitHub/GitLab/Bitbucket/self-hosted/local
path). Only Mode 1 (analyze — read-only) and Mode 2 (scaffold — generates
a migration worksheet, never source code) are implemented; Mode 3
(migrate) and Mode 4 (sync) are intentionally not — see
docs/FrameworkSync.md.

`analyze` never modifies the source repository. It also never assumes an
existing test suite should be migrated: it produces an "EXISTING
AUTOMATION INVENTORY" (tests/classes/suites/tags/Page Objects/API
clients/execution model, ...) as a read-only understanding of what
already exists — see docs/FrameworkSync.md, "Existing customer test
inventory."

`scaffold` only ever writes into `--output-dir` (default `generated/`,
gitignored). By default it covers every detected test (Mode C, "Full
Modernization Analysis") without migrating anything; pass `--scope`
(`directory`/`suite`/`tag`/`class`/`test`) with `--selector` to restrict
its "Migration candidates" section to exactly one subset (Mode B,
"Selective Migration") — every other test is left unmentioned and
untouched.

`recommend` is entirely optional (gated by `ai.enabled` — see
`framework.ai`): asks the configured `AIProvider` for a migration
suggestion per detected technology and writes them to `--output`, without
changing `--report`. Pass the resulting file to `scaffold --recommendations`
to fold them into the worksheet as a separate, clearly-labeled,
unverified section — deterministic analysis remains the worksheet's
primary content either way.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from framework.cli_common import run_command
from framework.sync.ai_recommendations import MappingRecommendation, recommend_mappings
from framework.sync.analyzer import RepositoryAnalyzer
from framework.sync.compatibility import compute_compatibility_report
from framework.sync.diff import diff_analyses
from framework.sync.models import MigrationScope, RepositoryAnalysis
from framework.sync.scaffold import generate_migration_worksheet
from framework.sync.sources import (
    GitRepositorySource,
    LocalDirectorySource,
    RepositorySource,
    ZipArchiveSource,
)
from framework.sync.test_inventory import format_inventory


def _resolve_source(raw: str) -> RepositorySource:
    if raw.endswith(".zip"):
        return ZipArchiveSource(raw)
    if raw.startswith(("http://", "https://", "git@", "ssh://", "file://")):
        # `GitRepositorySource` already documents `file://` as a supported
        # git remote (`git clone` accepts it natively) — this was simply
        # never wired to that prefix here, so a `file://` source fell
        # through to `LocalDirectorySource`, which rejects it outright
        # (`Path("file:///...").is_dir()` is never true) with a
        # technically-correct but confusing "Not a directory" error.
        return GitRepositorySource(raw)
    return LocalDirectorySource(raw)


def _cmd_analyze(args: argparse.Namespace) -> None:
    source = _resolve_source(args.source)
    root = source.materialize()
    try:
        analysis = RepositoryAnalyzer().analyze(root, source=args.source)
    finally:
        source.cleanup()

    analysis.save(args.report)
    report = compute_compatibility_report(analysis)
    print(f"Analyzed {analysis.structure.total_files} files ({analysis.primary_language}).")
    print(report.summary)
    print()

    ui_framework = next(
        (f.name for f in analysis.detected_frameworks if f.category == "ui_automation"), None
    )
    execution_model = analysis.execution_model
    print(
        format_inventory(
            analysis.inventory,
            language=analysis.primary_language,
            ui_framework=ui_framework,
            runner=execution_model.runner if execution_model else None,
            primary_execution=execution_model.command if execution_model else None,
            parallelism=execution_model.parallelism if execution_model else None,
        )
    )
    print()

    if analysis.findings:
        print(f"{len(analysis.findings)} finding(s) — see {args.report} for details.")
    print(f"Full analysis saved to {args.report}")


def _cmd_scaffold(args: argparse.Namespace) -> None:
    analysis = RepositoryAnalysis.load(args.report)

    ai_recommendations = None
    if args.recommendations:
        raw = json.loads(Path(args.recommendations).read_text(encoding="utf-8"))
        ai_recommendations = [MappingRecommendation.model_validate(item) for item in raw]

    scope = MigrationScope(args.scope)
    worksheet = generate_migration_worksheet(
        analysis,
        ai_recommendations=ai_recommendations,
        migration_scope=scope,
        migration_selector=args.selector,
    )

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target = output_path / "MIGRATION_WORKSHEET.md"
    target.write_text(worksheet, encoding="utf-8")
    print(f"Migration worksheet written to {target} — review before acting on it.")


def _cmd_diff(args: argparse.Namespace) -> None:
    before = RepositoryAnalysis.load(args.before)
    after = RepositoryAnalysis.load(args.after)
    result = diff_analyses(before, after)

    print(f"New frameworks: {result.new_frameworks or 'none'}")
    print(f"Removed frameworks: {result.removed_frameworks or 'none'}")
    print(f"File count delta: {result.file_count_delta:+d}")
    print(f"New findings: {len(result.new_findings)}")
    print(f"Resolved findings: {result.resolved_findings_count}")


def _cmd_recommend(args: argparse.Namespace) -> None:
    from framework.ai import get_provider
    from framework.config.settings import get_settings
    from framework.enums.environment import Environment

    analysis = RepositoryAnalysis.load(args.report)
    settings = get_settings(Environment(args.env))
    provider = get_provider(settings.ai)

    recommendations = recommend_mappings(analysis, provider)
    Path(args.output).write_text(
        json.dumps([r.model_dump(mode="json") for r in recommendations], indent=2),
        encoding="utf-8",
    )
    print(
        f"{len(recommendations)} recommendation(s) from provider '{provider.name}' "
        f"written to {args.output} — review before acting on any of them."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m framework.sync", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Mode 1 — read-only repository analysis")
    analyze_parser.add_argument("source", help="Local directory, .zip file, or git URL")
    analyze_parser.add_argument("--report", default="repository_analysis.json")
    analyze_parser.set_defaults(func=_cmd_analyze)

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="Mode 2 — generate a migration worksheet"
    )
    scaffold_parser.add_argument("--report", default="repository_analysis.json")
    scaffold_parser.add_argument("--output-dir", default="generated")
    scaffold_parser.add_argument(
        "--recommendations",
        default=None,
        help="Optional output of `recommend` to fold into the worksheet",
    )
    scaffold_parser.add_argument(
        "--scope",
        choices=[s.value for s in MigrationScope],
        default=MigrationScope.REPOSITORY.value,
        help=(
            "Migration-candidate selection granularity (Mode B, 'Selective Migration'). "
            "'repository' (default) analyzes every detected test; any other scope "
            "requires --selector and restricts the worksheet's 'Migration candidates' "
            "section to exactly that subset — every other test is left untouched."
        ),
    )
    scaffold_parser.add_argument(
        "--selector",
        default=None,
        help=(
            "Required unless --scope=repository. A directory path prefix (scope=directory), "
            "a source file path (scope=suite), a tag/group name (scope=tag), a class/"
            "describe-block name (scope=class), or a test identifier/name (scope=test)."
        ),
    )
    scaffold_parser.set_defaults(func=_cmd_scaffold)

    diff_parser = subparsers.add_parser("diff", help="Compare two saved analyses")
    diff_parser.add_argument("before")
    diff_parser.add_argument("after")
    diff_parser.set_defaults(func=_cmd_diff)

    recommend_parser = subparsers.add_parser(
        "recommend", help="Optional AI-assisted migration mapping suggestions"
    )
    recommend_parser.add_argument("--report", default="repository_analysis.json")
    recommend_parser.add_argument("--env", default="dev")
    recommend_parser.add_argument("--output", default="mapping_recommendations.json")
    recommend_parser.set_defaults(func=_cmd_recommend)

    args = parser.parse_args(argv)
    return run_command(args.func, args)


if __name__ == "__main__":
    sys.exit(main())
