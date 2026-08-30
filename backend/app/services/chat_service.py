"""Unified chat with durable, per-user turn serialization."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal
import uuid

from google.cloud import firestore
from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud.firestore_v1.query import Query

from ai.chat_agent import ChatAgent, ChatToolLoopLimitError
from app.errors import ConflictError, ExternalServiceError, NotFoundError
from app.models.chat import ChatMessage, ChatResponse, MessagesResponse
from app.services.cursor import decode_cursor, encode_cursor
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class ChatTurnConflictError(ConflictError):
    """The client must wait for/retrieve an existing turn, not run it again."""


class ChatTurnFailedError(ConflictError):
    """A turn may have reached an unknown external-model state exactly once."""


TurnClaim = Literal["acquired", "completed", "busy", "failed"]


class ChatService:
    def __init__(
        self,
        db: FirestoreClient,
        *,
        agent_factory: Callable[..., ChatAgent] | None = None,
        transactional_runner: Callable = firestore.transactional,
        clock: Callable[[], datetime] | None = None,
        turn_lease: timedelta = timedelta(minutes=5),
    ):
        self._db = db
        self.user_service = UserService(db)
        self._agent_factory = agent_factory or ChatAgent
        self._transactional_runner = transactional_runner
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._turn_lease = turn_lease

    @staticmethod
    def _turn_document_id(turn_id: str) -> str:
        return hashlib.sha256(turn_id.encode("utf-8")).hexdigest()

    @staticmethod
    def _message_ids(turn_id: str) -> tuple[str, str]:
        digest = hashlib.sha256(turn_id.encode("utf-8")).hexdigest()[:24]
        return f"msg-{digest}-user", f"msg-{digest}-agent"

    def _turn_ref(self, uid: str, turn_id: str):
        return self._db.collection("users").document(uid).collection("chat_turns").document(
            self._turn_document_id(turn_id)
        )

    def _state_ref(self, uid: str):
        return self._db.collection("users").document(uid).collection("chat_state").document("active")

    @staticmethod
    def _as_utc(value: object) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _claim_turn(self, uid: str, turn_id: str, text: str, channel: str) -> tuple[TurnClaim, dict[str, Any]]:
        turn_ref = self._turn_ref(uid, turn_id)
        state_ref = self._state_ref(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def claim_in_transaction(transaction):
            now = self._as_utc(self._clock())
            turn_snapshot = turn_ref.get(transaction=transaction)
            if turn_snapshot.exists:
                turn = turn_snapshot.to_dict() or {}
                if turn.get("text") != text or turn.get("channel") != channel:
                    raise ChatTurnConflictError("turnId is already bound to a different message")
                if turn.get("status") == "completed":
                    return "completed", turn
                if turn.get("status") in {"failed", "unknown"}:
                    return "failed", turn
                return "busy", turn

            state_snapshot = state_ref.get(transaction=transaction)
            state = state_snapshot.to_dict() or {}
            active_turn = state.get("activeTurnId")
            lease_until = self._as_utc(state.get("leaseUntil"))
            if isinstance(active_turn, str) and active_turn and lease_until and lease_until > now:
                return "busy", state
            if isinstance(active_turn, str) and active_turn:
                # The old AI request may have reached the provider after this
                # process died. Mark it unknown rather than invoke it again.
                transaction.update(
                    self._turn_ref(uid, active_turn),
                    {"status": "unknown", "updatedAt": now, "terminalError": "expired-turn-lease"},
                )
            sequence = int(state.get("nextSequence", 0)) + 1
            user_message_id, agent_message_id = self._message_ids(turn_id)
            turn = {
                "turnId": turn_id,
                "status": "processing",
                "sequence": sequence,
                "text": text,
                "channel": channel,
                "userMessageId": user_message_id,
                "agentMessageId": agent_message_id,
                "startedAt": now,
                "updatedAt": now,
                "leaseUntil": now + self._turn_lease,
            }
            transaction.set(turn_ref, turn)
            transaction.set(
                state_ref,
                {
                    "activeTurnId": turn_id,
                    "leaseUntil": now + self._turn_lease,
                    "nextSequence": sequence,
                    "updatedAt": now,
                },
            )
            return "acquired", turn

        return claim_in_transaction(transaction)

    def _complete_turn(self, uid: str, turn_id: str, response_text: str) -> None:
        turn_ref = self._turn_ref(uid, turn_id)
        state_ref = self._state_ref(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def complete_in_transaction(transaction):
            now = self._as_utc(self._clock())
            turn = (turn_ref.get(transaction=transaction).to_dict() or {})
            transaction.update(
                turn_ref,
                {
                    "status": "completed",
                    "response": response_text,
                    "completedAt": now,
                    "updatedAt": now,
                    "leaseUntil": None,
                    "terminalError": None,
                },
            )
            state = state_ref.get(transaction=transaction).to_dict() or {}
            if state.get("activeTurnId") == turn_id:
                transaction.set(
                    state_ref,
                    {"activeTurnId": None, "leaseUntil": None, "updatedAt": now},
                    merge=True,
                )

        complete_in_transaction(transaction)

    def _fail_turn(self, uid: str, turn_id: str, error_code: str) -> None:
        turn_ref = self._turn_ref(uid, turn_id)
        state_ref = self._state_ref(uid)
        transaction = self._db.transaction()

        @self._transactional_runner
        def fail_in_transaction(transaction):
            now = self._as_utc(self._clock())
            transaction.update(
                turn_ref,
                {
                    "status": "failed",
                    "terminalError": error_code,
                    "updatedAt": now,
                    "leaseUntil": None,
                },
            )
            state = state_ref.get(transaction=transaction).to_dict() or {}
            if state.get("activeTurnId") == turn_id:
                transaction.set(
                    state_ref,
                    {"activeTurnId": None, "leaseUntil": None, "updatedAt": now},
                    merge=True,
                )

        fail_in_transaction(transaction)

    async def process_message(
        self,
        uid: str,
        text: str,
        channel: Literal["web", "telegram"],
        turn_id: str | None = None,
    ) -> ChatResponse:
        """Run one serialized turn and return the stored response on replay."""
        profile = self.user_service.get_profile(uid)
        if not profile:
            raise NotFoundError("User profile not found")
        normalized_turn_id = (turn_id or f"server:{uuid.uuid4().hex}").strip()
        if not normalized_turn_id or len(normalized_turn_id) > 256:
            raise ValueError("turnId must be 1..256 characters")
        claim, turn = self._claim_turn(uid, normalized_turn_id, text, channel)
        if claim == "completed":
            return ChatResponse(
                response=turn["response"],
                messageId=turn["userMessageId"],
                agentMessageId=turn["agentMessageId"],
            )
        if claim == "busy":
            raise ChatTurnConflictError("Another turn for this user is in progress")
        if claim == "failed":
            raise ChatTurnFailedError("This turn reached a terminal model state; retry with a new turnId")

        messages_ref = self._db.collection("users").document(uid).collection("messages")
        now = self._as_utc(self._clock())
        user_ref = messages_ref.document(turn["userMessageId"])
        user_ref.set(
            {
                "id": turn["userMessageId"],
                "role": "user",
                "channel": channel,
                "text": text,
                "createdAt": now,
                "turnId": normalized_turn_id,
            }
        )
        history_data = self._history_before_turn(messages_ref, turn["userMessageId"])
        system_instruction = self._system_instruction(profile.goal, profile.intensity)
        try:
            agent = self._agent_factory(db=self._db, uid=uid, system_instruction=system_instruction)
            agent_response_text = await agent.generate_response(history_data, text)
        except ChatToolLoopLimitError as exc:
            self._fail_turn(uid, normalized_turn_id, "tool-loop-limit")
            raise ExternalServiceError("Chat tool limit reached; start a new turn") from exc
        except Exception as exc:
            self._fail_turn(uid, normalized_turn_id, type(exc).__name__)
            raise ExternalServiceError("Chat processing failed; start a new turn") from exc

        messages_ref.document(turn["agentMessageId"]).set(
            {
                "id": turn["agentMessageId"],
                "role": "agent",
                "channel": channel,
                "text": agent_response_text,
                "createdAt": self._as_utc(self._clock()),
                "turnId": normalized_turn_id,
            }
        )
        self._complete_turn(uid, normalized_turn_id, agent_response_text)
        return ChatResponse(
            response=agent_response_text,
            messageId=turn["userMessageId"],
            agentMessageId=turn["agentMessageId"],
        )

    @staticmethod
    def _history_before_turn(messages_ref, current_message_id: str) -> list[dict[str, str]]:
        history_docs = messages_ref.order_by("createdAt", direction="ASCENDING").order_by(
            "__name__", direction="ASCENDING"
        ).limit_to_last(11).get()
        return [
            {"role": data.get("role", "user"), "text": data.get("text", "")}
            for doc in history_docs
            if doc.id != current_message_id
            for data in [doc.to_dict() or {}]
        ][-10:]

    @staticmethod
    def _system_instruction(goal: str, intensity: str) -> str:
        instruction = (
            "You are Mark-I, an AI Developer Mentor. "
            f"The user's goal is: '{goal}'. "
            f"Your communication intensity is set to: '{intensity}'. "
        )
        if intensity == "chill":
            instruction += "Be supportive, gentle, and encouraging. Focus on the positives."
        elif intensity == "brutal":
            instruction += "Be direct, strict, and challenging. Do not sugarcoat feedback."
        else:
            instruction += "Be balanced, informative, and professionally encouraging."
        return instruction + " Provide clear, actionable advice in the user's language."

    def get_messages(
        self,
        uid: str,
        limit: int = 50,
        cursor: str | None = None,
        channel: Literal["web", "telegram"] | None = None,
    ) -> MessagesResponse:
        """Return chronological history with an ID tie-breaker cursor."""
        query = self._db.collection("users").document(uid).collection("messages")
        if channel:
            from google.cloud.firestore_v1.base_query import FieldFilter

            query = query.where(filter=FieldFilter("channel", "==", channel))
        query = query.order_by("createdAt", direction=Query.ASCENDING).order_by("__name__", direction=Query.ASCENDING)
        if cursor:
            created_at, document_id = decode_cursor(cursor)
            query = query.start_after({"createdAt": created_at, "__name__": document_id})
        docs = list(query.limit(limit + 1).stream())
        has_more = len(docs) > limit
        messages = [self._firestore_to_message(doc.to_dict() or {}) for doc in docs[:limit]]
        next_cursor = encode_cursor(messages[-1].createdAt, messages[-1].id) if has_more and messages else None
        return MessagesResponse(messages=messages, nextCursor=next_cursor, hasMore=has_more)

    @staticmethod
    def _firestore_to_message(data: dict) -> ChatMessage:
        created_at = data["createdAt"]
        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
        return ChatMessage(
            id=data["id"],
            role=data["role"],
            channel=data["channel"],
            text=data["text"],
            createdAt=created_at,
        )
