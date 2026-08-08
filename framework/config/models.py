from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from framework.database.enums import DbDialect
from framework.enums.browser_type import BrowserType
from framework.enums.environment import Environment
from framework.enums.validation_mode import ValidationMode


class BrowserConfig(BaseModel):
    browser: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    slow_mo_ms: int = 0
    viewport_width: int = 1920
    viewport_height: int = 1080
    action_timeout_ms: int = 15_000
    navigation_timeout_ms: int = 30_000
    trace_on_failure: bool = True
    video_on_failure: bool = True
    screenshot_on_failure: bool = True
    har_recording: bool = False


class UiConfig(BaseModel):
    base_url: HttpUrl
    login_username: str = ""
    login_password: str = ""


class OptionalUiConfig(BaseModel):
    """Like `UiConfig`, but for *additional* named UI targets
    (`EnvironmentSettings.ui_targets`) that may legitimately be
    unconfigured in a given environment/checkout — e.g. a real internal app
    only reachable from certain networks. `base_url` is nullable so an
    unset `${VAR:-}` (empty string) validates to `None` instead of failing
    settings load entirely; callers/fixtures should skip (not fail) when
    it's `None`.
    """

    base_url: HttpUrl | None = None
    login_username: str = ""
    login_password: str = ""

    @field_validator("base_url", mode="before")
    @classmethod
    def _blank_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class AuthConfig(BaseModel):
    """Playwright `storage_state` session reuse (see `framework.auth`).

    Disabled by default so existing suites and CI runs behave exactly as
    before; opt in per environment via ``auth.enabled: true`` in the
    environment YAML (or ``AUTOMATION_AUTH_ENABLED``).
    """

    enabled: bool = False
    state_dir: str = ".auth"
    profile: str = "user"
    max_age_seconds: int = 28_800  # 8h — safely under most enterprise SSO session limits


class ApiEndpointConfig(BaseModel):
    base_url: HttpUrl
    timeout_seconds: int = 30
    auth_type: str = "none"  # none | basic | bearer | oauth2 | api_key | mtls
    # basic auth reuses client_id/client_secret as username/password
    client_id: str = ""
    client_secret: str = ""
    token_url: str | None = None
    api_key: str = ""


class DatabaseConfig(BaseModel):
    enabled: bool = False
    dialect: DbDialect = DbDialect.POSTGRESQL
    host: str = ""
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    # Set instead of `password` to keep only ciphertext in YAML/committed
    # config; `CredentialResolver` decrypts it with AUTOMATION_DB_SECRET_KEY at
    # connection time. Leave empty (the default) to use `password` /
    # ${AUTOMATION_DB_PASSWORD} as-is — this is additive, not a replacement.
    encrypted_password: str = ""
    schema_name: str | None = None
    pool_size: int = 5
    pool_max_overflow: int = 10
    pool_timeout_seconds: int = 10
    pool_recycle_seconds: int = 1800
    query_timeout_seconds: int = 30
    connect_args: dict[str, Any] = Field(default_factory=dict)


class ClickHouseConfig(BaseModel):
    """ClickHouse connection settings — a dedicated layer
    (`framework.database.clickhouse`), not routed through the existing
    SQLAlchemy-based `DatabaseConfig`/`DbDialect` (ClickHouse isn't one of
    its supported dialects, and the two shouldn't be conflated). `enabled`
    defaults to `False` so an unconfigured environment never fails
    settings load or tries to connect.
    """

    enabled: bool = False
    host: str = ""
    port: int = 8123
    database: str = ""
    username: str = ""
    password: str = ""
    protocol: str = "http"  # http | https
    timeout_seconds: int = 30


class FeatureFlags(BaseModel):
    """Capability switches for this framework's modular architecture.

    Core automation (`framework.pages`/`framework.api`/`framework.database`/
    `framework.network`/`framework.reporting`) never imports from an
    optional package (`framework.discovery`, `framework.sync`,
    `framework.ai`) — these flags gate CLI entry points and any call site
    that chooses to check them, not import-time behavior, so every optional
    capability can be added or removed without touching core code. See
    docs/ModularArchitecture.md for the full capability matrix.
    """

    # Core capabilities — safe to disable per environment, but never gated
    # behind an optional package import.
    database_validation: bool = False
    api_validation: bool = False
    network_interception: bool = True
    visual_validation: bool = False

    # Optional capabilities — off by default everywhere; each one is an
    # independent, separately importable package under framework/.
    discovery: bool = False
    framework_sync: bool = False
    ai_assistance: bool = False
    code_generation: bool = False
    self_healing_locators: bool = False
    ai_root_cause_analysis: bool = False


class AIConfig(BaseModel):
    """AI assistance configuration (`framework.ai`) — optional; the core
    framework behaves identically whether this is enabled or not.
    `provider` selects which `AIProvider` `framework.ai.get_provider()`
    builds (`none` — the default, always available; `openai_compatible` —
    any endpoint speaking the OpenAI chat-completions API shape, which
    covers cloud OpenAI/Azure OpenAI and self-hosted/local servers like
    Ollama/vLLM/LM Studio without hardcoding a vendor). `api_key` should
    only ever come from `${VAR:-}` env-var substitution (like
    `DatabaseConfig.password`) — never a literal value in a committed YAML
    file.
    """

    enabled: bool = False
    provider: str = "none"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: int = 30
    temperature: float = 0.2


class EnvironmentSettings(BaseModel):
    environment: Environment
    validation_mode: ValidationMode = ValidationMode.UI_ONLY
    ui: UiConfig
    ui_targets: dict[str, OptionalUiConfig] = Field(default_factory=dict)
    api: dict[str, ApiEndpointConfig] = Field(default_factory=dict)
    database: dict[str, DatabaseConfig] = Field(default_factory=dict)
    clickhouse: dict[str, ClickHouseConfig] = Field(default_factory=dict)
    ai: AIConfig = Field(default_factory=AIConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    parallel_workers: int = 4
