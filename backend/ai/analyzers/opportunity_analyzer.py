import json
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from vertexai.generative_models import GenerationConfig, GenerativeModel

from app.config import Settings, get_settings


class OpportunityAnalysisTerminalError(ValueError):
    """The provider returned data that cannot enter the persistence boundary."""


class OpportunityAnalysisRetryableError(RuntimeError):
    """The provider was unavailable; the Pub/Sub event must be retried."""


class OpportunityAnalysisSchema(BaseModel):
    """Only an explicit, bounded relevance assessment is durable."""

    model_config = ConfigDict(extra="forbid")

    relevance_score: int = Field(ge=1, le=10)
    reasoning: str = Field(min_length=1, max_length=2_000)
    concept: str = Field(min_length=1, max_length=100)

    @field_validator("reasoning", "concept", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class OpportunityAnalyzerAdapter(Protocol):
    """Credential-free provider seam used by worker and unit tests."""

    def generate(self, prompt: str) -> str:
        """Return the raw JSON response from the model provider."""


class VertexOpportunityAnalyzerAdapter:
    """Vertex implementation which creates a model only when called."""

    def __init__(
        self,
        model_name: str,
        *,
        model_factory: Callable[[str], Any] = GenerativeModel,
    ) -> None:
        self._model_name = model_name
        self._model_factory = model_factory

    def generate(self, prompt: str) -> str:
        model = self._model_factory(self._model_name)
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(response_mime_type="application/json"),
        )
        return response.text


class OpportunityAnalyzer:
    """Build a bounded prompt and validate output before worker persistence."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        adapter: OpportunityAnalyzerAdapter | None = None,
    ) -> None:
        settings = settings or get_settings()
        self._adapter = adapter or VertexOpportunityAnalyzerAdapter(settings.GEMINI_MODEL)

    def analyze_opportunity(
        self,
        opportunity_data: dict[str, Any],
        user_goal: str,
        user_skills: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = f"""
You are an AI Developer Mentor evaluating an opportunity (article, tutorial, job, etc.) for your mentee.

Opportunity Data:
Title: {opportunity_data.get('title')}
Description: {opportunity_data.get('description')}
Tags: {opportunity_data.get('tags')}

Mentee Profile:
Goal: {user_goal}
Current Skills: {json.dumps(user_skills)}

Evaluate this opportunity's relevance for the mentee. Respond with JSON only, with exactly:
- relevance_score: integer 1 through 10
- reasoning: concise explanation grounded in the goal
- concept: one main programming concept or skill
"""
        try:
            raw = self._adapter.generate(prompt)
            return OpportunityAnalysisSchema.model_validate(json.loads(raw)).model_dump()
        except (json.JSONDecodeError, ValidationError) as exc:
            raise OpportunityAnalysisTerminalError(
                "Opportunity analyzer returned invalid structured output"
            ) from exc
        except OpportunityAnalysisTerminalError:
            raise
        except Exception as exc:
            raise OpportunityAnalysisRetryableError("Opportunity analyzer is unavailable") from exc
