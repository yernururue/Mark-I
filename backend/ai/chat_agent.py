import logging
from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, Content, Part
from google.cloud.firestore_v1.client import Client as FirestoreClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ChatAgent:
    def __init__(self, system_instruction: str):
        self.system_instruction = system_instruction
        self.model = GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=[system_instruction]
        )

    async def generate_response(self, history_data: List[Dict[str, Any]], new_message: str) -> str:
        """
        history_data: List of dicts with 'role' ('user' or 'agent') and 'text'.
        """
        history = []
        for msg in history_data:
            role = msg.get("role")
            # Vertex AI uses 'user' and 'model'
            vertex_role = "user" if role == "user" else "model"
            text = msg.get("text", "")
            history.append(
                Content(role=vertex_role, parts=[Part.from_text(text)])
            )
        
        try:
            chat = self.model.start_chat(history=history)
            response = await chat.send_message_async(new_message)
            return response.text
        except Exception as e:
            logger.error(f"Error during ChatAgent generate_response: {e}")
            return "I'm having trouble processing that right now. Please try again later."
