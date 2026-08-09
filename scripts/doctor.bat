@echo off
REM Thin wrapper for "poetry run python -m framework doctor" — forwards
REM every argument as-is. No logic lives here; see framework\doctor\__main__.py.
REM
REM Usage: scripts\doctor.bat [--check] [--fix] [--dry-run] [--browser <name>] [--report <path>]
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.."
poetry run python -m framework doctor %*
