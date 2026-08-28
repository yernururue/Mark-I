"""Deterministic escalation facts derived from persisted GitHub analysis."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.decision_service import ESCALATION_RULES


def calculate_escalation_flags(
    *,
    concept_existed: bool,
    previous_score: float | None,
    updated_score: float,
    sentiment: str,
    recent_sentiments: Sequence[str],
) -> list[str]:
    """Return only policy-supported flags, with stable order for explainability."""
    flags: list[str] = []
    prior = previous_score if previous_score is not None else 0.0
    if not concept_existed:
        flags.append("new_concept")
    if concept_existed and updated_score <= prior - 1.0:
        flags.append("skill_regression")
    if any(prior < milestone <= updated_score for milestone in (5.0, 8.0)):
        flags.append("milestone_reached")
    if sentiment == "negative" and len(recent_sentiments) == 3 and all(
        item == "negative" for item in recent_sentiments
    ):
        flags.append("repeated_error")
    return [flag for flag in flags if flag in ESCALATION_RULES]
