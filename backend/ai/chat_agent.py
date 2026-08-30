import logging
from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, Content, Part, HarmCategory, HarmBlockThreshold, SafetySetting
from google.cloud.firestore_v1.client import Client as FirestoreClient
from app.config import Settings, get_settings
from tenacity import retry, stop_after_attempt, wait_exponential
from ai.tools.profile import profile_tool

logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(self, db: FirestoreClient, uid: str, system_instruction: str, settings: Settings | None = None):
        self._db = db
        settings = settings or get_settings()
        self.uid = uid
        self.system_instruction = system_instruction
        
        # Security settings to prevent jailbreaks / harmful generation
        safety_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
        ]
        
        self.model = GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=[system_instruction],
            tools=[profile_tool],
            safety_settings=safety_settings
        )

    def _get_user_skills(self) -> dict:
        doc = self._db.collection("users").document(self.uid).get()
        if doc.exists:
            return {"skills": doc.to_dict().get("skills", {})}
        return {"skills": {}}

    def _get_recent_observations(self, limit: int = 5) -> dict:
        docs = self._db.collection("users").document(self.uid).collection("observations").order_by(
            "createdAt", direction="DESCENDING"
        ).limit(limit).get()
        
        obs = []
        for doc in docs:
            data = doc.to_dict()
            obs.append({
                "summary": data.get("summary"),
                "concept": data.get("concept"),
                "significance": data.get("significanceScore"),
                "createdAt": str(data.get("createdAt"))
            })
        return {"observations": obs}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_response(self, history_data: List[Dict[str, Any]], new_message: str) -> str:
        """
        history_data: List of dicts with 'role' ('user' or 'agent') and 'text'.
        """
        history = []
        for msg in history_data:
            role = msg.get("role")
            vertex_role = "user" if role == "user" else "model"
            text = msg.get("text", "")
            history.append(
                Content(role=vertex_role, parts=[Part.from_text(text)])
            )
        
        try:
            chat = self.model.start_chat(history=history)
            response = await chat.send_message_async(new_message)
            
            # Handle Function Calling loop
            while response.function_call:
                func_call = response.function_call
                func_name = func_call.name
                
                logger.info(f"ChatAgent executing tool: {func_name}")
                
                api_response = {}
                if func_name == "get_user_skills":
                    api_response = self._get_user_skills()
                elif func_name == "get_recent_observations":
                    limit = int(func_call.args.get("limit", 5))
                    api_response = self._get_recent_observations(limit)
                else:
                    api_response = {"error": f"Unknown function: {func_name}"}
                
                # Send the function response back to the model
                response = await chat.send_message_async(
                    Part.from_function_response(
                        name=func_name,
                        response=api_response
                    )
                )
                
            return response.text
            
        except Exception as e:
            logger.error(f"Error during ChatAgent generate_response: {e}")
            return "I'm having trouble processing that right now. Please try again later."
