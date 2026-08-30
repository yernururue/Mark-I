from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from google.genai import types
from pydantic import ValidationError

from ai.agent import GithubObservationSchema
from ai.analyzers.github_analyzer import (
    AdkGitHubAnalyzerAdapter,
    GitHubAnalysisRetryableError,
    GitHubAnalysisTerminalError,
    analyze_github_event,
)
from ai.analyzers.opportunity_analyzer import (
    OpportunityAnalysisRetryableError,
    OpportunityAnalysisTerminalError,
    OpportunityAnalyzer,
    VertexOpportunityAnalyzerAdapter,
)
from app.config import ConfigurationError, RuntimeEnvironment, RuntimeRole, Settings


VALID_ANALYSIS = {
    "summary": "The patch adds deterministic retry coverage.",
    "concept": "distributed-systems",
    "sentiment": "positive",
    "proficiencyAssessment": 7.5,
    "significanceScore": 8,
}


class StaticAdapter:
    def __init__(self, result: object = VALID_ANALYSIS, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return json.dumps(self.result)


def analyze_with(adapter: StaticAdapter) -> GithubObservationSchema:
    return asyncio.run(
        analyze_github_event(
            repo="alex/repo",
            event_type="push",
            ref="refs/heads/main",
            commit_count=1,
            changes_text="@@ -1 +1 @@\n-old\n+new",
            adapter=adapter,
        )
    )


def test_analyzer_uses_injected_adapter_without_credentials():
    adapter = StaticAdapter()

    result = analyze_with(adapter)

    assert result == GithubObservationSchema(**VALID_ANALYSIS)
    assert "@@ -1 +1 @@" in adapter.prompts[0]
    assert "proficiency" in adapter.prompts[0].lower()


def test_adk_adapter_passes_typed_user_content():
    captured: dict[str, object] = {}

    class Sessions:
        async def create_session(self, **kwargs):
            captured["session"] = kwargs
            return SimpleNamespace(id="session-1")

    class FinalEvent:
        content = SimpleNamespace(parts=[SimpleNamespace(text=json.dumps(VALID_ANALYSIS))])

        @staticmethod
        def is_final_response() -> bool:
            return True

    class FakeRunner:
        def run_async(self, **kwargs):
            captured["run"] = kwargs

            async def events():
                yield FinalEvent()

            return events()

    def runner_factory(**kwargs):
        captured["runner"] = kwargs
        return FakeRunner()

    adapter = AdkGitHubAnalyzerAdapter(
        agent_factory=lambda: object(),
        session_service_factory=Sessions,
        runner_factory=runner_factory,
    )

    output = asyncio.run(adapter.generate("analyze this patch"))

    message = captured["run"]["new_message"]
    assert isinstance(message, types.Content)
    assert message.role == "user"
    assert message.parts[0].text == "analyze this patch"
    assert json.loads(output) == VALID_ANALYSIS


@pytest.mark.parametrize(
    "invalid",
    [
        {**VALID_ANALYSIS, "concept": "   "},
        {**VALID_ANALYSIS, "sentiment": "excited"},
        {**VALID_ANALYSIS, "proficiencyAssessment": 11},
        {**VALID_ANALYSIS, "unexpected": True},
    ],
)
def test_invalid_model_output_is_terminal(invalid):
    with pytest.raises(GitHubAnalysisTerminalError):
        analyze_with(StaticAdapter(invalid))


def test_provider_failure_is_retryable():
    with pytest.raises(GitHubAnalysisRetryableError):
        analyze_with(StaticAdapter(error=TimeoutError("provider timed out")))


class StaticOpportunityAdapter:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result or {"relevance_score": 8, "reasoning": "Fits the goal.", "concept": "fastapi"}
        self.error = error
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return json.dumps(self.result)


def test_opportunity_analyzer_uses_injected_adapter_without_model_or_credentials():
    adapter = StaticOpportunityAdapter()
    analyzer = OpportunityAnalyzer(Settings(_env_file=None, GEMINI_MODEL="test-model"), adapter=adapter)

    result = analyzer.analyze_opportunity({"title": "FastAPI"}, "Build backend services", {"python": 6})

    assert result == {"relevance_score": 8, "reasoning": "Fits the goal.", "concept": "fastapi"}
    assert "Build backend services" in adapter.prompts[0]


def test_vertex_opportunity_adapter_defers_model_creation_until_generate():
    created: list[str] = []

    class Model:
        def generate_content(self, prompt, generation_config):
            assert prompt == "prompt"
            assert "application/json" in str(generation_config)
            return SimpleNamespace(text='{"relevance_score": 7, "reasoning": "yes", "concept": "python"}')

    adapter = VertexOpportunityAnalyzerAdapter("model", model_factory=lambda name: created.append(name) or Model())
    assert created == []
    assert json.loads(adapter.generate("prompt"))["concept"] == "python"
    assert created == ["model"]


@pytest.mark.parametrize(
    "result",
    [
        {"relevance_score": 0, "reasoning": "no", "concept": "python"},
        {"relevance_score": 7, "reasoning": " ", "concept": "python"},
        {"relevance_score": 7, "reasoning": "yes", "concept": "python", "extra": True},
    ],
)
def test_invalid_opportunity_model_output_is_terminal(result):
    analyzer = OpportunityAnalyzer(Settings(_env_file=None), adapter=StaticOpportunityAdapter(result))
    with pytest.raises(OpportunityAnalysisTerminalError):
        analyzer.analyze_opportunity({}, "goal", {})


def test_opportunity_provider_failure_is_retryable_without_a_fallback_write():
    analyzer = OpportunityAnalyzer(
        Settings(_env_file=None), adapter=StaticOpportunityAdapter(error=TimeoutError("provider timeout"))
    )
    with pytest.raises(OpportunityAnalysisRetryableError):
        analyzer.analyze_opportunity({}, "goal", {})


def test_unknown_runtime_environment_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV="prodution")


def test_production_api_requires_telegram_runtime_configuration():
    settings = Settings(
        _env_file=None,
        ENV=RuntimeEnvironment.PRODUCTION,
        GCP_PROJECT_ID="project",
        GITHUB_CLIENT_ID="client",
        GITHUB_CLIENT_SECRET="secret",
        GITHUB_WEBHOOK_SECRET="webhook-secret",
        WEBHOOK_BASE_URL=None,
        TELEGRAM_BOT_TOKEN=None,
        TELEGRAM_BOT_USERNAME=None,
        TELEGRAM_WEBHOOK_URL=None,
        TELEGRAM_WEBHOOK_SECRET=None,
    )

    with pytest.raises(ConfigurationError) as exc_info:
        settings.validate_for_role(RuntimeRole.API)

    message = str(exc_info.value)
    assert "TELEGRAM_BOT_TOKEN" in message
    assert "TELEGRAM_WEBHOOK_SECRET" in message
    assert "secret" not in message.lower().replace("telegram_webhook_secret", "")
