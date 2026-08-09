#!/usr/bin/env bash
# Thin wrapper for `poetry run python -m framework.extension run` — forwards
# every argument as-is. No logic lives here; see framework/extension/run.py.
#
# Usage: scripts/extension-run.sh --framework <path> --url <url> [--scaffold] [--dry-run] ...
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
poetry run python -m framework.extension run "$@"
