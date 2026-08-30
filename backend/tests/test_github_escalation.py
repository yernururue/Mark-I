from __future__ import annotations

import pytest

from workers.github_escalation import calculate_escalation_flags


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"concept_existed": False, "previous_score": None, "updated_score": 4.0, "sentiment": "positive", "recent_sentiments": ["positive"]}, ["new_concept"]),
        ({"concept_existed": True, "previous_score": 7.0, "updated_score": 5.9, "sentiment": "neutral", "recent_sentiments": ["neutral"]}, ["skill_regression"]),
        ({"concept_existed": True, "previous_score": 4.9, "updated_score": 5.0, "sentiment": "positive", "recent_sentiments": ["positive"]}, ["milestone_reached"]),
        ({"concept_existed": True, "previous_score": 7.9, "updated_score": 8.2, "sentiment": "positive", "recent_sentiments": ["positive"]}, ["milestone_reached"]),
        ({"concept_existed": True, "previous_score": 4.0, "updated_score": 4.0, "sentiment": "negative", "recent_sentiments": ["negative", "negative", "negative"]}, ["repeated_error"]),
        ({"concept_existed": True, "previous_score": 4.0, "updated_score": 4.0, "sentiment": "negative", "recent_sentiments": ["negative", "positive", "negative"]}, []),
    ],
)
def test_escalation_flags_are_deterministic_and_supported(kwargs, expected):
    assert calculate_escalation_flags(**kwargs) == expected


def test_negative_sentiment_alone_is_not_an_escalation_flag():
    assert calculate_escalation_flags(
        concept_existed=True,
        previous_score=4.0,
        updated_score=4.0,
        sentiment="negative",
        recent_sentiments=["negative"],
    ) == []
