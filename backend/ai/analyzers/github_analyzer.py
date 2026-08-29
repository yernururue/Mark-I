import logging
import json

from pydantic import ValidationError

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from ai.agent import get_github_analyzer_config, GithubObservationSchema
from ai.prompts import GITHUB_ANALYZER_SYSTEM_PROMPT, GITHUB_ANALYZER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class GitHubAnalysisTerminalError(ValueError):
    """The model response is unusable and retrying the same delivery cannot fix it."""


class GitHubAnalysisRetryableError(RuntimeError):
    """The analyzer boundary was unavailable; worker delivery may be retried."""

async def analyze_github_event(
    repo: str,
    event_type: str,
    ref: str,
    commit_count: int,
    changes_text: str
) -> GithubObservationSchema:
    """
    Analyzes a GitHub event using Gemini and returns a structured observation.
    Raises a typed error so the worker can distinguish ACK-worthy malformed
    output from a Pub/Sub-retryable runtime failure.
    """
    config = get_github_analyzer_config(GITHUB_ANALYZER_SYSTEM_PROMPT)
    prompt = GITHUB_ANALYZER_USER_PROMPT_TEMPLATE.format(
        event_type=event_type,
        repo=repo,
        ref=ref,
        commit_count=commit_count,
        changes_text=changes_text
    )

    try:
        sessions = InMemorySessionService()
        session = await sessions.create_session(app_name="mark-i", user_id="github-worker")
        runner = Runner(app_name="mark-i", agent=config, session_service=sessions)
        async for event in runner.run_async(user_id="github-worker", session_id=session.id, new_message=prompt):
            if event.is_final_response() and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    return GithubObservationSchema.model_validate(json.loads(text))
        raise GitHubAnalysisTerminalError("GitHub analyzer produced no structured response")
    except (json.JSONDecodeError, ValidationError) as exc:
        raise GitHubAnalysisTerminalError("GitHub analyzer returned invalid structured output") from exc
    except GitHubAnalysisTerminalError:
        raise
    except Exception as exc:
        raise GitHubAnalysisRetryableError("GitHub analyzer is unavailable") from exc
