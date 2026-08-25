import os
import json
import asyncio
import logging
import html
from google.cloud import pubsub_v1
from google.cloud import firestore

from backend.app.config import get_settings
from backend.ai.analyzers.github_analyzer import analyze_github_event
from backend.app.services.observation_service import ObservationService
from backend.app.services.skill_service import SkillService
from backend.app.services.decision_service import DecisionService
from backend.app.services.telegram_service import TelegramService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
observation_service = ObservationService(db)
skill_service = SkillService(db)
decision_service = DecisionService(db)
telegram_service = TelegramService(db)

def get_changes_text(event_type: str, payload: dict) -> str:
    """Extracts relevant text from payload to feed to Gemini."""
    text = ""
    if event_type == "push":
        commits = payload.get("commits", [])
        for c in commits:
            text += f"Commit Message: {c.get('message', '')}\n"
            text += f"Added: {c.get('added', [])}\n"
            text += f"Removed: {c.get('removed', [])}\n"
            text += f"Modified: {c.get('modified', [])}\n\n"
    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        text += f"PR Title: {pr.get('title', '')}\n"
        text += f"PR Body: {pr.get('body', '')}\n"
    return text

async def process_message_async(message: pubsub_v1.subscriber.message.Message):
    """Processes a single Pub/Sub message asynchronously."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        logger.info(f"Processing event: {data.get('event_type')}")
        
        uid = data.get("uid")
        if not uid:
            logger.warning("No uid found in message. Acknowledging and skipping.")
            message.ack()
            return

        payload = data.get("payload", {})
        event_type = data.get("event_type", "unknown")
        
        repo_name = payload.get("repository", {}).get("full_name", "unknown/repo")
        ref = payload.get("ref", "")
        commit_count = len(payload.get("commits") or []) if event_type == "push" else 1
        
        changes_text = get_changes_text(event_type, payload)
        
        # Analyze using Gemini
        observation_data = await analyze_github_event(
            repo=repo_name,
            event_type=event_type,
            ref=ref,
            commit_count=commit_count,
            changes_text=changes_text
        )
        
        if observation_data:
            # Create Observation
            metadata = {
                "repo": repo_name,
                "event": event_type,
                "ref": ref,
                "commitCount": commit_count,
            }
            observation = observation_service.create_observation(
                uid=uid,
                source="github",
                summary=observation_data.summary,
                concept=observation_data.concept,
                sentiment=observation_data.sentiment,
                significance_score=observation_data.significanceScore,
                metadata=metadata
            )
            
            # Update Skill
            # For simplicity, we use the raw significance score as assessment
            skill_service.update_skill(
                uid=uid,
                concept=observation_data.concept,
                assessment=observation_data.significanceScore,
                weight=0.3
            )
            
            # Decision Policy
            user_doc = db.collection("users").document(uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                intensity = user_data.get("intensity", "normal")
                telegram_user_id = user_data.get("telegramUserId")
                
                escalation_flags = []
                if observation_data.sentiment == "negative":
                    escalation_flags.append("negative_sentiment")
                    
                should_notify, reason = False, ""
                if observation_data.significanceScore is not None:
                    should_notify, reason = decision_service.evaluate_and_log(
                        uid=uid,
                        observation_id=observation.id,
                        significance=observation_data.significanceScore,
                        intensity=intensity,
                        escalation_flags=escalation_flags
                    )
                
                if should_notify and telegram_user_id:
                    msg = (
                        f"🤖 <b>Mark-I GitHub Analysis</b>\n\n"
                        f"<b>Concept:</b> <code>{html.escape(observation_data.concept)}</code>\n"
                        f"<b>Summary:</b> {html.escape(observation_data.summary)}\n\n"
                        f"<i>(Reason for ping: {html.escape(reason)})</i>"
                    )
                    await telegram_service.send_message(telegram_user_id, msg)
            
            logger.info(f"Successfully processed and updated skill '{observation_data.concept}' for user {uid}")
        
        # Ack the message
        message.ack()

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Nack the message so it can be retried
        message.nack()

def callback(message: pubsub_v1.subscriber.message.Message):
    # Run the async process function in the current event loop
    asyncio.run(process_message_async(message))

def main():
    subscriber = pubsub_v1.SubscriberClient()
    # Assume subscription name is the topic name + "-sub"
    subscription_path = subscriber.subscription_path(settings.GCP_PROJECT_ID, f"{settings.PUBSUB_GITHUB_TOPIC}-sub")
    
    logger.info(f"Listening for messages on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
    except Exception as e:
        logger.error(f"Listening failed: {e}")

if __name__ == "__main__":
    main()
