import pydantic
from google.adk.agents import LlmAgent

from app.config import Settings, get_settings

class GithubObservationSchema(pydantic.BaseModel):
    summary: str
    concept: str
    sentiment: str
    proficiencyAssessment: float = pydantic.Field(ge=0, le=10)
    significanceScore: int = pydantic.Field(ge=1, le=10)

def get_github_analyzer_config(system_instruction: str, settings: Settings | None = None) -> LlmAgent:
    """Returns ADK Agent config for GitHub Analysis."""
    settings = settings or get_settings()
    return LlmAgent(
        name="github_observation_analyzer",
        model=settings.GEMINI_MODEL,
        instruction=system_instruction,
        output_schema=GithubObservationSchema,
    )
