"""At-least-once opportunity transport with durable per-user effects."""

from __future__ import annotations

import asyncio
import html
import json
import logging
from typing import Any

from google.cloud import firestore, pubsub_v1

from ai.analyzers.opportunity_analyzer import OpportunityAnalyzer
from app.config import RuntimeRole, Settings, get_settings
from app.services.opportunity_effect_service import OpportunityEffectService
from app.services.processed_event_service import DeliveryClaimStatus, ProcessedEventService
from app.services.telegram_service import TelegramSendResult, TelegramService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkerContext:
    def __init__(self, settings: Settings, db):
        self.settings = settings
        self.db = db
        self.telegram_service = TelegramService(db, settings)
        self.effect_service = OpportunityEffectService(db)
        self.delivery_service = ProcessedEventService(db)
        self.opportunity_analyzer = OpportunityAnalyzer(settings)


def build_context(settings: Settings | None = None) -> WorkerContext:
    settings = settings or get_settings()
    settings.validate_for_role(RuntimeRole.OPPORTUNITY_WORKER)
    db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
    return WorkerContext(settings, db)


async def _send_notification(service: TelegramService, chat_id: int, text: str) -> TelegramSendResult:
    send_result = getattr(service, "send_message_result", None)
    if callable(send_result):
        return await send_result(chat_id, text, parse_mode="HTML")
    delivered = await service.send_message(chat_id, text, parse_mode="HTML")
    return TelegramSendResult(delivered=bool(delivered), retryable=not delivered)


async def _deliver_if_needed(uid: str, effects, opportunity: dict[str, Any], analysis: dict[str, Any], context: WorkerContext) -> None:
    if not effects.should_notify or not effects.delivery_id or effects.delivery_status != "pending":
        return
    assert effects.decision_id is not None
    claim = context.delivery_service.claim_delivery(effects.delivery_id, uid, effects.decision_id)
    if claim is DeliveryClaimStatus.ACQUIRED:
        message = (
            "🌟 <b>New Opportunity Found!</b>\n\n"
            f"<b>Title:</b> {html.escape(str(opportunity.get('title', '')))}\n"
            f"<b>Concept:</b> <code>{html.escape(str(analysis['concept']))}</code>\n"
            f"<b>Relevance:</b> {analysis['relevance_score']}/10\n\n"
            f"{html.escape(str(analysis['reasoning']))}"
        )
        result = await _send_notification(context.telegram_service, effects.telegram_chat_id, message)
        if result.delivered:
            context.delivery_service.mark_delivery(effects.delivery_id, uid, effects.decision_id, "sent")
        elif result.ambiguous:
            context.delivery_service.mark_delivery(effects.delivery_id, uid, effects.decision_id, "unknown", result.error)
        else:
            context.delivery_service.mark_delivery(effects.delivery_id, uid, effects.decision_id, "failed", result.error)
            if result.retryable:
                raise RuntimeError("Retryable Telegram opportunity delivery failure")
    elif claim is DeliveryClaimStatus.BUSY:
        raise RuntimeError("Opportunity Telegram delivery lease is busy")
    # sent/suppressed/unknown are terminal and deliberately not sent again.


async def process_opportunity_for_user(uid: str, user_data: dict, data: dict, context: WorkerContext):
    goal = user_data.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        return
    event_id = data.get("eventId")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("Opportunity eventId is required")
    effects = context.effect_service.get(uid=uid, event_id=event_id)
    if effects is None:
        analysis = context.opportunity_analyzer.analyze_opportunity(data, goal, user_data.get("skills", {}))
        effects = context.effect_service.apply(
            uid=uid,
            event_id=event_id,
            opportunity=data,
            analysis=analysis,
        )
    else:
        # A redelivery must never re-run AI or write business data. This small
        # structure is used only if an earlier Telegram delivery is still pending.
        analysis = {"concept": "opportunity", "relevance_score": 0, "reasoning": ""}
    await _deliver_if_needed(uid, effects, data, analysis, context)


async def process_message_async(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    """Process every eligible user; durable effect rows absorb Pub/Sub retries."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Opportunity message must be an object")
        # Bound model work for a shared source event; a large user base must not
        # turn one Pub/Sub delivery into unbounded provider concurrency.
        semaphore = asyncio.Semaphore(10)

        async def process_user(user_doc) -> None:
            async with semaphore:
                await process_opportunity_for_user(user_doc.id, user_doc.to_dict() or {}, data, context)

        tasks = [process_user(user_doc) for user_doc in context.db.collection("users").stream()]
        if tasks:
            await asyncio.gather(*tasks)
        message.ack()
    except Exception as exc:
        logger.exception("Retrying opportunity event after %s", type(exc).__name__)
        message.nack()


def callback(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    asyncio.run(process_message_async(message, context))


def main():
    context = build_context()
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        context.settings.GCP_PROJECT_ID,
        f"{context.settings.PUBSUB_OPPORTUNITY_TOPIC}-sub",
    )
    logger.info("Listening for opportunities on %s", subscription_path)
    future = subscriber.subscribe(subscription_path, callback=lambda message: callback(message, context))
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()
    except Exception:
        logger.exception("Opportunity worker listener failed")


if __name__ == "__main__":
    main()
