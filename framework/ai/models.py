from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class RecommendationConfidence(str, Enum):
    """How much certainty backs a piece of information — used throughout
    `framework.discovery`/`framework.sync`/`framework.ai` so a caller (or
    a human reviewer) never mistakes a guess for a confirmed fact.
    """

    DISCOVERED = "discovered"  # deterministic, directly observed evidence
    INFERRED = "inferred"  # deterministic heuristic, lower certainty
    AI_SUGGESTED = "ai_suggested"  # produced by an AI provider, unverified
    MANUALLY_CONFIRMED = "manually_confirmed"  # a human has reviewed and approved it


class AIRecommendation(BaseModel):
    """An AI (or deterministic-fallback) suggestion. Always a
    recommendation, never something the framework acts on automatically —
    `confidence` starts at `AI_SUGGESTED` (or `DISCOVERED` for a
    deterministic fallback) and only becomes `MANUALLY_CONFIRMED` once a
    human sets it explicitly.
    """

    text: str
    confidence: RecommendationConfidence
    provider: str
    raw: dict[str, Any] | None = None
