"""Compatibility export for deterministic escalation facts."""

from app.services.decision_service import calculate_escalation_flags

__all__ = ["calculate_escalation_flags"]
