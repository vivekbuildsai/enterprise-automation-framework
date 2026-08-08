from __future__ import annotations

import re

# Best-effort deterministic filter — not a guarantee. Callers remain
# responsible for not putting real secrets into prompts/context in the
# first place; this exists as a defense-in-depth layer before anything
# leaves the process toward an AI provider.
_KEY_VALUE_SECRET = re.compile(
    r"(?i)\b(password|passwd|pwd|api[\s_-]?key|secret|token|authorization|cookie)\b\s*[:=]\s*\S+"
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-_.]+")


def redact_secrets(text: str) -> str:
    """Strips anything that looks like a credential/token/password before
    it's sent to an AI provider.
    """
    redacted = _BEARER_TOKEN.sub("Bearer [REDACTED]", text)
    redacted = _KEY_VALUE_SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", redacted)
    return redacted
