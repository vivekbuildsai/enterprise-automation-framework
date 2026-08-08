from __future__ import annotations

from framework.sync.models import AnalysisDiff, RepositoryAnalysis


def diff_analyses(before: RepositoryAnalysis, after: RepositoryAnalysis) -> AnalysisDiff:
    """Compares two `RepositoryAnalysis` snapshots of the same
    repository (e.g. two branches, or the same branch analyzed twice) —
    the read-only comparison half of "Sync Mode 4", without the
    diff-driven re-application Mode 4 would also require (not
    implemented — see `SyncMode`).
    """
    before_names = {f.name for f in before.detected_frameworks}
    after_names = {f.name for f in after.detected_frameworks}

    before_finding_keys = {(f.file, f.line, f.category) for f in before.findings}
    after_finding_keys = {(f.file, f.line, f.category) for f in after.findings}

    return AnalysisDiff(
        new_frameworks=sorted(after_names - before_names),
        removed_frameworks=sorted(before_names - after_names),
        file_count_delta=after.structure.total_files - before.structure.total_files,
        new_findings=[
            finding
            for finding in after.findings
            if (finding.file, finding.line, finding.category) not in before_finding_keys
        ],
        resolved_findings_count=len(before_finding_keys - after_finding_keys),
    )
