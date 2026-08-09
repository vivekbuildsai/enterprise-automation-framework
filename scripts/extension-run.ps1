# Thin wrapper for "poetry run python -m framework.extension run" —
# forwards every argument as-is. No logic lives here; see
# framework/extension/run.py.
#
# Usage: .\scripts\extension-run.ps1 --framework <path> --url <url> [--scaffold] [--dry-run] ...
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
poetry run python -m framework.extension run @Args
