"""Path-containment guarantees for scaffold output — the same "resolved
target must stay under resolved root" discipline
`framework.sync.sources.ZipArchiveSource._safe_target` already uses for
zip-slip protection during archive extraction, applied here to *writing*
generated files instead. Every scaffold write goes through this module;
nothing in `framework.extension` touches disk any other way.

Generated customer automation must always land inside the customer's own
project (`framework.project_root.PROJECT_ROOT`) — never inside this
package's own installed location (`site-packages/framework/`), and never
outside the project root at all, even if a caller passes an unusual
`--output-dir`.
"""

from __future__ import annotations

from pathlib import Path

from framework.exceptions import ConfigurationError
from framework.project_root import PROJECT_ROOT


def resolve_scaffold_output_dir(output_dir: str | Path) -> Path:
    """Resolves `output_dir` against `PROJECT_ROOT` (if relative) and
    refuses anything that resolves outside it — including a relative path
    that escapes via `..` segments, or an absolute path pointing somewhere
    else entirely (e.g. accidentally passed as `/usr/lib/.../site-packages`).
    """
    raw = Path(output_dir)
    candidate = raw if raw.is_absolute() else PROJECT_ROOT / raw
    resolved = candidate.resolve()
    project_root_resolved = PROJECT_ROOT.resolve()

    if resolved != project_root_resolved and project_root_resolved not in resolved.parents:
        raise ConfigurationError(
            f"Refusing to write scaffold output outside the project root: {resolved} "
            f"(project root: {project_root_resolved})"
        )
    return resolved


def safe_scaffold_target(output_root: Path, relative_path: str) -> Path:
    """Resolves one generated file's path under `output_root` and refuses
    path traversal (`../`, an embedded absolute path, a symlink escape) —
    the same check `ZipArchiveSource._safe_target` applies to untrusted zip
    members. `relative_path` here traces back to a discovered page
    title/URL rather than direct user input, but it is still never trusted
    blindly: a page titled e.g. `"../../etc/passwd"` must not escape
    `output_root`.
    """
    target = (output_root / relative_path).resolve()
    if target != output_root and output_root not in target.parents:
        raise ConfigurationError(f"Unsafe generated file path (path traversal): {relative_path!r}")
    return target
