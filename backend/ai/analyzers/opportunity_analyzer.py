import logging
import json
from vertexai.generative_models import GenerativeModel, GenerationConfig
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class OpportunityAnalyzer:
    def __init__(self):
        self.model = GenerativeModel(settings.GEMINI_MODEL)

    def analyze_opportunity(self, opportunity_data: dict, user_goal: str, user_skills: dict) -> dict:
        """
        Evaluates the relevance of an opportunity against the user's goal and skills.
        Returns a dict with:
          - relevance_score (int 1-10)
          - reasoning (str)
          - concept (str)
        """
        prompt = f"""
        You are an AI Developer Mentor evaluating an opportunity (article, tutorial, job, etc.) for your mentee.
        
        Opportunity Data:
        Title: {opportunity_data.get('title')}
        Description: {opportunity_data.get('description')}
        Tags: {opportunity_data.get('tags')}
        
        Mentee Profile:
        Goal: {user_goal}
        Current Skills: {json.dumps(user_skills)}
        
        Evaluate this opportunity's relevance for the mentee.
        A highly relevant opportunity directly helps them achieve their goal or improve weak skills.
        
        You must respond in valid JSON format with exactly three fields:
        "relevance_score": An integer from 1 to 10 (10 being highly relevant).
        "reasoning": A short paragraph explaining why it's relevant or not, in the context of their goal.
        "concept": The main programming concept or skill this opportunity relates to (e.g., "react", "testing").
        """
        
        config = GenerationConfig(response_mime_type="application/json")
        
        try:
            response = self.model.generate_content(prompt, generation_config=config)
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Failed to analyze opportunity: {e}")
            return {
                "relevance_score": 0,
                "reasoning": "Failed to analyze",
                "concept": "unknown"
            }
