# Thin wrapper for "poetry run python -m framework doctor" — forwards
# every argument as-is. No logic lives here; see framework/doctor/__main__.py.
#
# Usage: .\scripts\doctor.ps1 [--check] [--fix] [--dry-run] [--browser <name>] [--report <path>]
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")
poetry run python -m framework doctor @Args
