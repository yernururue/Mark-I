import asyncio
import logging
import html
from pydantic import ValidationError
from google.cloud import pubsub_v1
from google.cloud import firestore

from app.config import RuntimeRole, Settings, get_settings
from app.models.github import GitHubEventEnvelope
from app.services.observation_service import ObservationService
from app.services.skill_service import SkillService
from app.services.decision_service import DecisionService
from app.services.telegram_service import TelegramService
from app.services.processed_event_service import EventClaimStatus, ProcessedEventService
from workers.github_extractors import UnsupportedGitHubEvent, extract_github_event
from workers.github_escalation import calculate_escalation_flags

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerContext:
    def __init__(self, settings: Settings, db):
        self.settings = settings
        self.db = db
        self.observation_service = ObservationService(db)
        self.skill_service = SkillService(db)
        self.decision_service = DecisionService(db)
        self.telegram_service = TelegramService(db, settings)
        self.processed_event_service = ProcessedEventService(db)


def build_context(settings: Settings | None = None) -> WorkerContext:
    settings = settings or get_settings()
    settings.validate_for_role(RuntimeRole.GITHUB_WORKER)
    db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
    return WorkerContext(settings, db)

def decode_github_event_envelope(data: bytes) -> GitHubEventEnvelope:
    """Validate the publisher's canonical message without key translation."""
    return GitHubEventEnvelope.model_validate_json(data)


async def process_message_async(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    """Processes a single Pub/Sub message asynchronously."""
    envelope = None
    claim_acquired = False
    try:
        envelope = decode_github_event_envelope(message.data)
        logger.info("Processing GitHub event %s for delivery %s", envelope.eventType, envelope.deliveryId)

        claim_status = context.processed_event_service.claim(envelope.deliveryId, envelope.uid)
        if claim_status is EventClaimStatus.COMPLETED:
            message.ack()
            return
        if claim_status is EventClaimStatus.BUSY:
            message.nack()
            return
        claim_acquired = True

        uid = envelope.uid
        try:
            event_context = extract_github_event(envelope)
        except UnsupportedGitHubEvent:
            logger.info("Acknowledging unsupported GitHub event %s", envelope.eventType)
            context.processed_event_service.complete(envelope.deliveryId, envelope.uid)
            message.ack()
            return
        
        # Analyze using Gemini
        from ai.analyzers.github_analyzer import analyze_github_event
        observation_data = await analyze_github_event(
            repo=event_context.repo,
            event_type=event_context.eventType,
            ref=event_context.ref or "",
            commit_count=int(event_context.metadata.get("commitCount", 1)),
            changes_text=event_context.changesText,
        )
        
        if observation_data:
            user_doc = context.db.collection("users").document(uid).get()
            if not user_doc.exists:
                raise LookupError(f"GitHub event user {uid!r} does not exist")
            user_data = user_doc.to_dict() or {}
            existing_skills = user_data.get("skills") or {}
            concept_existed = observation_data.concept in existing_skills
            previous_score = existing_skills.get(observation_data.concept)

            # Create Observation
            metadata = {
                **event_context.metadata,
                "ref": event_context.ref,
            }
            observation = context.observation_service.create_observation(
                uid=uid,
                source="github",
                summary=observation_data.summary,
                concept=observation_data.concept,
                sentiment=observation_data.sentiment,
                significance_score=observation_data.significanceScore,
                metadata=metadata,
                observation_id=f"github-{envelope.deliveryId}-{uid}",
            )
            
            # Proficiency is a skill input; significance belongs only to decisions.
            updated_score = context.skill_service.update_skill(
                uid=uid,
                concept=observation_data.concept,
                assessment=observation_data.proficiencyAssessment,
                weight=0.3,
                processed_event_id=context.processed_event_service.document_id(envelope.deliveryId, uid),
            )
            
            intensity = user_data.get("intensity", "normal")
            telegram_user_id = user_data.get("telegramUserId")
            recent_observations = context.observation_service.get_recent_observations(
                uid, limit=3, concept=observation_data.concept
            )
            escalation_flags = calculate_escalation_flags(
                concept_existed=concept_existed,
                previous_score=previous_score,
                updated_score=updated_score,
                sentiment=observation_data.sentiment,
                recent_sentiments=[item.sentiment for item in recent_observations],
            )
            should_notify, reason = context.decision_service.evaluate_and_log(
                uid=uid,
                observation_id=observation.id,
                significance=observation_data.significanceScore,
                intensity=intensity,
                escalation_flags=escalation_flags,
                decision_id=f"github-{envelope.deliveryId}-{uid}",
            )

            if should_notify and telegram_user_id and context.processed_event_service.claim_effect(
                envelope.deliveryId, uid, "telegramNotification"
            ):
                msg = (
                    f"🤖 <b>Mark-I GitHub Analysis</b>\n\n"
                    f"<b>Concept:</b> <code>{html.escape(observation_data.concept)}</code>\n"
                    f"<b>Summary:</b> {html.escape(observation_data.summary)}\n\n"
                    f"<i>(Reason for ping: {html.escape(reason)})</i>"
                )
                await context.telegram_service.send_message(telegram_user_id, msg)
            
            logger.info(f"Successfully processed and updated skill '{observation_data.concept}' for user {uid}")
        
        context.processed_event_service.complete(envelope.deliveryId, envelope.uid)
        message.ack()

    except ValidationError:
        logger.warning("Acknowledging invalid GitHub event envelope")
        message.ack()
    except Exception as exc:
        logger.exception("Recoverable error processing GitHub event: %s", type(exc).__name__)
        if envelope is not None and claim_acquired:
            context.processed_event_service.release_for_retry(
                envelope.deliveryId,
                envelope.uid,
                type(exc).__name__,
            )
        message.nack()

def callback(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    # Run the async process function in the current event loop
    asyncio.run(process_message_async(message, context))

def main():
    context = build_context()
    subscriber = pubsub_v1.SubscriberClient()
    # Assume subscription name is the topic name + "-sub"
    subscription_path = subscriber.subscription_path(context.settings.GCP_PROJECT_ID, f"{context.settings.PUBSUB_GITHUB_TOPIC}-sub")
    
    logger.info(f"Listening for messages on {subscription_path}...\n")
    
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=lambda message: callback(message, context))
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
    except Exception as e:
        logger.error(f"Listening failed: {e}")

if __name__ == "__main__":
    main()
