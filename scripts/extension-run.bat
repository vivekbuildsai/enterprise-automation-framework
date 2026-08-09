@echo off
REM Thin wrapper for "poetry run python -m framework.extension run" —
REM forwards every argument as-is. No logic lives here; see
REM framework\extension\run.py.
REM
REM Usage: scripts\extension-run.bat --framework <path> --url <url> [--scaffold] [--dry-run] ...
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."
poetry run python -m framework.extension run %*
