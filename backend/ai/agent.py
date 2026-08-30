from typing import Literal

import pydantic
from google.adk.agents import LlmAgent

from app.config import Settings, get_settings

class GithubObservationSchema(pydantic.BaseModel):
    """Validated boundary between non-deterministic model output and business state."""

    model_config = pydantic.ConfigDict(extra="forbid")

    summary: str = pydantic.Field(min_length=1, max_length=1000)
    concept: str = pydantic.Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    sentiment: Literal["positive", "negative", "neutral"]
    proficiencyAssessment: float = pydantic.Field(ge=0, le=10)
    significanceScore: int = pydantic.Field(ge=1, le=10)

    @pydantic.field_validator("summary", "concept", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

def get_github_analyzer_config(system_instruction: str, settings: Settings | None = None) -> LlmAgent:
    """Returns ADK Agent config for GitHub Analysis."""
    settings = settings or get_settings()
    return LlmAgent(
        name="github_observation_analyzer",
        model=settings.GEMINI_MODEL,
        instruction=system_instruction,
        output_schema=GithubObservationSchema,
    )
