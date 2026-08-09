"""Safe `.env` updates — reuses this framework's existing dotenv-layering
configuration architecture (`framework.config.settings`: real process env
vars > `.env.{environment}` > `.env`) rather than inventing a competing
config file format. `doctor --fix` only ever writes to `.env` (the
existing, already-gitignored, user-owned override layer every environment
YAML's `${VAR:-default}` placeholders already read from) — it never edits
`config/environments/*.yaml`, which stays the checked-in, human-owned
default layer.

Every write here is non-destructive by construction: an existing `KEY=`
line already set to a *different* value is left untouched unless the
caller explicitly passes `force=True`; a line already set to the *same*
value is a no-op either way. `dry_run=True` computes and returns the same
change description without touching the file at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from framework.project_root import PROJECT_ROOT

_KEY_LINE_PATTERN_TEMPLATE = r"^(?P<key>{key})\s*=\s*(?P<value>.*)$"


@dataclass(frozen=True, slots=True)
class EnvChange:
    """One proposed (or applied) `.env` change — always inspectable before
    it's written, matching the `--check`/`--fix`/`--dry-run` contract.
    """

    key: str
    old_value: str | None
    new_value: str
    action: str  # "add" | "update" | "unchanged" | "skipped_conflict"


def default_env_path() -> Path:
    return PROJECT_ROOT / ".env"


def _read_lines(env_path: Path) -> list[str]:
    if not env_path.exists():
        return []
    return env_path.read_text(encoding="utf-8").splitlines()


def plan_env_change(
    key: str, new_value: str, *, env_path: Path | None = None, force: bool = False
) -> EnvChange:
    """Computes what *would* change — never writes. Every caller (`--fix`
    and `--fix --dry-run` alike) goes through this first, so the preview
    and the real write can never disagree.
    """
    path = env_path or default_env_path()
    lines = _read_lines(path)
    pattern = re.compile(_KEY_LINE_PATTERN_TEMPLATE.format(key=re.escape(key)))

    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        existing_value = match.group("value").strip()
        if existing_value == new_value:
            return EnvChange(
                key=key, old_value=existing_value, new_value=new_value, action="unchanged"
            )
        if force:
            return EnvChange(
                key=key, old_value=existing_value, new_value=new_value, action="update"
            )
        return EnvChange(
            key=key, old_value=existing_value, new_value=new_value, action="skipped_conflict"
        )

    return EnvChange(key=key, old_value=None, new_value=new_value, action="add")


def apply_env_change(change: EnvChange, *, env_path: Path | None = None) -> None:
    """Writes exactly the change `plan_env_change` already computed —
    `action="unchanged"`/`"skipped_conflict"` are no-ops by construction
    (nothing to write), so this is always safe to call unconditionally
    after a plan.
    """
    if change.action in ("unchanged", "skipped_conflict"):
        return

    path = env_path or default_env_path()
    lines = _read_lines(path)
    pattern = re.compile(_KEY_LINE_PATTERN_TEMPLATE.format(key=re.escape(change.key)))
    new_line = f"{change.key}={change.new_value}"

    if change.action == "update":
        lines = [new_line if pattern.match(line) else line for line in lines]
    else:  # "add"
        lines.append(new_line)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
