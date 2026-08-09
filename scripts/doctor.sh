#!/usr/bin/env bash
# Thin wrapper for `poetry run python -m framework doctor` — forwards every
# argument as-is. No logic lives here; see framework/doctor/__main__.py.
#
# Usage: scripts/doctor.sh [--check] [--fix] [--dry-run] [--browser <name>] [--report <path>]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
poetry run python -m framework doctor "$@"
