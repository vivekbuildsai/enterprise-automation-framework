from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

import yaml
from dotenv import dotenv_values, load_dotenv

from framework.config.models import EnvironmentSettings
from framework.enums.environment import Environment
from framework.exceptions import ConfigurationError
from framework.project_root import PROJECT_ROOT

# Re-bound as a module attribute (not used directly) so
# `monkeypatch.setattr(settings_module, "_PROJECT_ROOT", tmp_path)` in
# tests/config/unit/test_settings.py keeps working unchanged — every
# function below reads `_PROJECT_ROOT`/`_CONFIG_DIR` from this module's own
# namespace at call time, not from `framework.project_root` directly. See
# `framework.project_root` for the actual resolution logic (the one
# canonical resolver every path-sensitive module shares).
_PROJECT_ROOT = PROJECT_ROOT
_CONFIG_DIR = _PROJECT_ROOT / "config" / "environments"
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-(.*?))?\}")


def _resolve_env_placeholders(value: Any) -> Any:
    """Recursively substitute ``${VAR_NAME}`` / ``${VAR_NAME:-default}`` tokens
    in YAML values with real environment variables, so secrets never live in
    the YAML files themselves.
    """
    if isinstance(value, str):

        def _replace(match: re.Match[str]) -> str:
            var_name, default = match.group(1), match.group(2)
            return os.environ.get(var_name, default if default is not None else "")

        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    return value


def _load_yaml(environment: Environment) -> dict[str, Any]:
    config_path = _CONFIG_DIR / f"{environment.value}.yaml"
    if not config_path.exists():
        raise ConfigurationError(
            f"No environment config found for '{environment.value}' at {config_path}"
        )
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    resolved: dict[str, Any] = _resolve_env_placeholders(raw)
    return resolved


@lru_cache(maxsize=len(Environment))
def get_settings(environment: Environment | None = None) -> EnvironmentSettings:
    """Load and validate settings for the given environment (or the current
    ``AUTOMATION_ENV``). Cached per-environment so repeated calls are cheap and every
    consumer within a test run shares the same validated object.

    Dotenv files are layered, highest precedence first:
    1. Real process environment variables (CI secrets, shell exports) — never
       overridden by any file, per ``load_dotenv(..., override=False)``.
    2. ``.env.{environment}`` — per-environment overrides (BASE_URL,
       USERNAME, PASSWORD, TIMEOUTS, HEADLESS, BROWSER, ...). Optional; a
       missing file is silently skipped.
    3. ``.env`` — shared defaults common to every environment.
    This mirrors the dotenv-flow / Next.js ``.env.[mode]`` convention.
    """
    # `.env`'s AUTOMATION_ENV (if any) is only a fallback for environment
    # resolution itself — read via `dotenv_values` (parse-only, no
    # os.environ mutation) so it can never shadow a real process env var
    # or the .env.{environment} file selected below.
    base_env_defaults = dotenv_values(_PROJECT_ROOT / ".env")
    automation_env = (
        os.environ.get("AUTOMATION_ENV")
        or base_env_defaults.get("AUTOMATION_ENV")
        or Environment.DEV.value
    )
    env = environment or Environment(automation_env)

    load_dotenv(_PROJECT_ROOT / f".env.{env.value}", override=False)
    load_dotenv(_PROJECT_ROOT / ".env", override=False)

    raw = _load_yaml(env)
    raw["environment"] = env.value

    try:
        return EnvironmentSettings.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError, yaml errors, etc.
        raise ConfigurationError(
            f"Invalid configuration for environment '{env.value}': {exc}"
        ) from exc


def clear_settings_cache() -> None:
    """Test-only helper to bust the settings cache between isolated test runs."""
    get_settings.cache_clear()
