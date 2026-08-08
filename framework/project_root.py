"""The single authoritative resolver for a project's root directory — the
one concept every module that reads/writes project-owned data (environment
config, `.env*`, `artifacts/`, `logs/`, `.auth/`, `data/testdata/`,
`config/dashboards/`) must agree on, instead of each independently computing
`Path(__file__).resolve().parents[N]` (correct only while developing inside
this repo — once genuinely `pip install`ed elsewhere, that resolves *inside*
`site-packages/`, see docs/GettingStarted.md).

PACKAGE ROOT (where `framework/` itself lives, e.g. `site-packages/framework/`
once installed) and PROJECT ROOT (the customer's own automation project, or
this repo's own checkout during framework development) are never the same
thing once the framework is installed as a dependency — this module always
returns the latter.

Precedence:
1. ``AUTOMATION_PROJECT_ROOT`` env var, if set — explicit escape hatch for
   the rare case the project root isn't the current working directory (an
   IDE run configuration, a CI job with an unusual cwd, ...).
2. The current working directory, if it looks like a project root (has a
   `config/environments/` directory — the one thing every project using
   this framework has, including this repo's own dev checkout).
3. This package's own location, two parents above `framework/` — the
   pre-existing in-repo fallback (e.g. a one-off script run from an
   unrelated cwd), preserved so existing behavior doesn't change when a
   project-root `config/` genuinely can't be found.
"""

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_MARKER = Path("config") / "environments"


def resolve_project_root() -> Path:
    explicit = os.environ.get("AUTOMATION_PROJECT_ROOT")
    if explicit:
        return Path(explicit).expanduser().resolve()

    cwd = Path.cwd()
    if (cwd / _PROJECT_MARKER).is_dir():
        return cwd

    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = resolve_project_root()
