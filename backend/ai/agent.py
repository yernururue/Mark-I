import pydantic
from google.antigravity import LocalAgentConfig

from backend.app.config import get_settings

settings = get_settings()

class GithubObservationSchema(pydantic.BaseModel):
    summary: str
    concept: str
    sentiment: str
    significanceScore: int

def get_github_analyzer_config(system_instruction: str) -> LocalAgentConfig:
    """Returns ADK Agent config for GitHub Analysis."""
    return LocalAgentConfig(
        system_instruction=system_instruction,
        response_schema=GithubObservationSchema,
        model_name=settings.GEMINI_MODEL,
        # Defaulting to no-auth or ADC if vertex isn't fully configured, 
        # assuming GOOGLE_API_KEY or ADC is in the env as per requirements
    )
