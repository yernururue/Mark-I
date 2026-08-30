import os
import json
import asyncio
import logging
import html
from google.cloud import pubsub_v1
from google.cloud import firestore

from app.config import RuntimeRole, Settings, get_settings
from ai.analyzers.opportunity_analyzer import OpportunityAnalyzer
from app.services.observation_service import ObservationService
from app.services.decision_service import DecisionService
from app.services.telegram_service import TelegramService
from app.services.user_service import UserService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerContext:
    def __init__(self, settings: Settings, db):
        self.settings = settings
        self.db = db
        self.observation_service = ObservationService(db)
        self.decision_service = DecisionService(db)
        self.telegram_service = TelegramService(db, settings)
        self.user_service = UserService(db)
        self.opportunity_analyzer = OpportunityAnalyzer(settings)


def build_context(settings: Settings | None = None) -> WorkerContext:
    settings = settings or get_settings()
    settings.validate_for_role(RuntimeRole.OPPORTUNITY_WORKER)
    db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
    return WorkerContext(settings, db)

async def process_opportunity_for_user(uid: str, user_data: dict, data: dict, context: WorkerContext):
    goal = user_data.get("goal")
    skills = user_data.get("skills", {})
    intensity = user_data.get("intensity", "normal")
    telegram_user_id = user_data.get("telegramUserId")
    
    if not goal or not telegram_user_id:
        return

    # Analyze relevance
    result = context.opportunity_analyzer.analyze_opportunity(data, goal, skills)
    score = result.get("relevance_score", 0)
    reasoning = result.get("reasoning", "")
    concept = result.get("concept", "general")
    
    if score >= 7:
        # Create Observation
        metadata = {
            "sourceUrl": data.get("sourceUrl"),
            "sourceName": data.get("sourceName"),
            "title": data.get("title")
        }
        
        observation = context.observation_service.create_observation(
            uid=uid,
            source="opportunity",
            summary=f"Found relevant opportunity: {data.get('title')}. {reasoning}",
            concept=concept,
            sentiment="positive",
            significance_score=score,
            metadata=metadata
        )
        
        # Decision Policy
        should_notify, reason = context.decision_service.evaluate_and_log(
            uid=uid,
            observation_id=observation.id,
            significance=score,
            intensity=intensity,
            escalation_flags=[]
        )
        
        if should_notify:
            msg = (
                f"🌟 <b>New Opportunity Found!</b>\n\n"
                f"<b>Title:</b> {html.escape(data.get('title', ''))}\n"
                f"<b>Concept:</b> <code>{html.escape(concept)}</code>\n"
                f"<b>Relevance:</b> {score}/10\n\n"
                f"{html.escape(reasoning)}\n\n"
                f"<a href='{data.get('sourceUrl', '')}'>Read More</a>"
            )
            await context.telegram_service.send_message(telegram_user_id, msg)
            logger.info(f"Notified user {uid} about opportunity {data.get('title')}")


async def process_message_async(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    """Processes a single Pub/Sub message asynchronously."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        logger.info(f"Processing opportunity: {data.get('title')}")
        
        # In a real app we'd fetch active users only, or do batching.
        users_ref = context.db.collection("users")
        users_stream = users_ref.stream()
        
        tasks = []
        for user_doc in users_stream:
            uid = user_doc.id
            user_data = user_doc.to_dict()
            tasks.append(process_opportunity_for_user(uid, user_data, data, context))
            
        if tasks:
            await asyncio.gather(*tasks)
            
        message.ack()
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        message.nack()

def callback(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    asyncio.run(process_message_async(message, context))

def main():
    context = build_context()
    subscriber = pubsub_v1.SubscriberClient()
    topic_name = context.settings.PUBSUB_OPPORTUNITY_TOPIC
    subscription_path = subscriber.subscription_path(context.settings.GCP_PROJECT_ID, f"{topic_name}-sub")
    
    logger.info(f"Listening for opportunities on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=lambda message: callback(message, context))
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
    except Exception as e:
        logger.error(f"Listening failed: {e}")

if __name__ == "__main__":
    main()
