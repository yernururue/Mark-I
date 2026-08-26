import logging
from datetime import datetime, timezone
import uuid
from typing import List

from google.cloud.firestore_v1.client import Client as FirestoreClient
from app.services.user_service import UserService
from ai.chat_agent import ChatAgent

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: FirestoreClient):
        self._db = db
        self.user_service = UserService(db)

    async def process_message(self, uid: str, text: str, channel: str) -> str:
        """
        Обрабатывает новое сообщение от пользователя:
        1. Сохраняет сообщение пользователя
        2. Загружает историю и профиль
        3. Запрашивает агента
        4. Сохраняет ответ агента
        5. Возвращает текст ответа
        """
        # 1. Загружаем профиль пользователя
        profile = self.user_service.get_profile(uid)
        if not profile:
            return "Error: User profile not found."

        # 2. Сохраняем сообщение пользователя
        msg_ref = self._db.collection("users").document(uid).collection("messages").document()
        user_msg = {
            "id": msg_ref.id,
            "role": "user",
            "channel": channel,
            "text": text,
            "createdAt": datetime.now(timezone.utc)
        }
        msg_ref.set(user_msg)

        # 3. Загружаем историю чата (последние 10 сообщений, кроме текущего)
        messages_ref = self._db.collection("users").document(uid).collection("messages")
        history_docs = messages_ref.order_by(
            "createdAt", direction="ASCENDING"
        ).limit_to_last(11).get() # Fetch a bit more to ensure we have enough after filtering

        history_data = []
        # Исключаем текущее сообщение явно по ID, чтобы избежать race conditions
        for doc in history_docs:
            if doc.id == msg_ref.id:
                continue
            doc_data = doc.to_dict()
            history_data.append({
                "role": doc_data.get("role"),
                "text": doc_data.get("text")
            })
        
        # Оставляем только последние 10 сообщений
        history_data = history_data[-10:]

        # 4. Формируем системный промпт с учетом интенсивности и целей
        intensity = profile.intensity
        goal = profile.goal
        
        system_instruction = (
            f"You are Mark-I, an AI Developer Mentor. "
            f"The user's goal is: '{goal}'. "
            f"Your communication intensity is set to: '{intensity}'. "
        )

        if intensity == "chill":
            system_instruction += "Be very supportive, gentle, and encouraging. Focus on the positives."
        elif intensity == "brutal":
            system_instruction += "Be extremely direct, strict, and challenging. Do not sugarcoat anything. Push them hard."
        else:
            system_instruction += "Be balanced, informative, and moderately encouraging. Act like a professional mentor."

        system_instruction += "\nProvide clear, actionable, and concise advice. Always reply in the language the user is speaking."

        # 5. Запрашиваем агента
        agent = ChatAgent(db=self._db, uid=uid, system_instruction=system_instruction)
        agent_response_text = await agent.generate_response(history_data, text)

        # 6. Сохраняем ответ агента
        reply_ref = self._db.collection("users").document(uid).collection("messages").document()
        agent_msg = {
            "id": reply_ref.id,
            "role": "agent",
            "channel": channel,
            "text": agent_response_text,
            "createdAt": datetime.now(timezone.utc)
        }
        reply_ref.set(agent_msg)

        return agent_response_text
