import logging
from typing import Optional

from google.antigravity import Agent

from backend.ai.agent import get_github_analyzer_config, GithubObservationSchema
from backend.ai.prompts import GITHUB_ANALYZER_SYSTEM_PROMPT, GITHUB_ANALYZER_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

async def analyze_github_event(
    repo: str,
    event_type: str,
    ref: str,
    commit_count: int,
    changes_text: str
) -> Optional[GithubObservationSchema]:
    """
    Analyzes a GitHub event using Gemini and returns a structured observation.
    Returns None if parsing fails or an error occurs.
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
        async with Agent(config) as agent:
            response = await agent.chat(prompt)
            data = await response.structured_output()
            if data:
                return GithubObservationSchema.model_validate(data)
            else:
                logger.error("Failed to parse structured output from Gemini.")
                return None
    except Exception as e:
        logger.error(f"Error during Gemini analysis: {e}")
        return None
