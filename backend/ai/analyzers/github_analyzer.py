import json
import logging
from collections.abc import Callable
from typing import Protocol

from pydantic import ValidationError

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ai.agent import get_github_analyzer_config, GithubObservationSchema
from ai.prompts import GITHUB_ANALYZER_SYSTEM_PROMPT, GITHUB_ANALYZER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class GitHubAnalysisTerminalError(ValueError):
    """The model response is unusable and retrying the same delivery cannot fix it."""


class GitHubAnalysisRetryableError(RuntimeError):
    """The analyzer boundary was unavailable; worker delivery may be retried."""


class GitHubAnalyzerAdapter(Protocol):
    """Credential-free seam for the model provider boundary."""

    async def generate(self, prompt: str) -> str:
        """Return the provider's raw structured response."""


class AdkGitHubAnalyzerAdapter:
    """Google ADK implementation; construction itself performs no network I/O."""

    def __init__(
        self,
        *,
        agent_factory: Callable[[], object] | None = None,
        session_service_factory: Callable[[], object] = InMemorySessionService,
        runner_factory: Callable[..., object] = Runner,
    ) -> None:
        self._agent_factory = agent_factory or (
            lambda: get_github_analyzer_config(GITHUB_ANALYZER_SYSTEM_PROMPT)
        )
        self._session_service_factory = session_service_factory
        self._runner_factory = runner_factory

    async def generate(self, prompt: str) -> str:
        sessions = self._session_service_factory()
        session = await sessions.create_session(app_name="mark-i", user_id="github-worker")
        runner = self._runner_factory(
            app_name="mark-i",
            agent=self._agent_factory(),
            session_service=sessions,
        )
        message = types.Content(role="user", parts=[types.Part(text=prompt)])
        async for event in runner.run_async(
            user_id="github-worker",
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    return text
        raise GitHubAnalysisTerminalError("GitHub analyzer produced no structured response")


async def analyze_github_event(
    repo: str,
    event_type: str,
    ref: str,
    commit_count: int,
    changes_text: str,
    *,
    adapter: GitHubAnalyzerAdapter | None = None,
) -> GithubObservationSchema:
    """
    Analyzes a GitHub event using Gemini and returns a structured observation.
    Raises a typed error so the worker can distinguish ACK-worthy malformed
    output from a Pub/Sub-retryable runtime failure.
    """
    prompt = GITHUB_ANALYZER_USER_PROMPT_TEMPLATE.format(
        event_type=event_type,
        repo=repo,
        ref=ref,
        commit_count=commit_count,
        changes_text=changes_text
    )

    try:
        raw_output = await (adapter or AdkGitHubAnalyzerAdapter()).generate(prompt)
        return GithubObservationSchema.model_validate(json.loads(raw_output))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise GitHubAnalysisTerminalError("GitHub analyzer returned invalid structured output") from exc
    except GitHubAnalysisTerminalError:
        raise
    except Exception as exc:
        raise GitHubAnalysisRetryableError("GitHub analyzer is unavailable") from exc
