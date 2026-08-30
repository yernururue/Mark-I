import asyncio
import logging
import html
import httpx
from google.cloud import pubsub_v1
from google.cloud import firestore
from google.cloud import secretmanager

from app.config import RuntimeRole, Settings, get_settings
from app.models.github import GitHubEventEnvelope
from app.services.telegram_service import TelegramSendResult, TelegramService
from app.services.processed_event_service import DeliveryClaimStatus, EventClaimStatus, ProcessedEventService
from app.services.github_evidence_service import GitHubEvidenceService
from workers.github_extractors import UnsupportedGitHubEvent, extract_github_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_terminal_processing_error(exc: Exception) -> bool:
    """Classify errors that cannot become valid on a Pub/Sub redelivery."""
    return isinstance(exc, (ValueError, LookupError))

class WorkerContext:
    def __init__(self, settings: Settings, db, evidence_service: GitHubEvidenceService):
        self.settings = settings
        self.db = db
        self.telegram_service = TelegramService(db, settings)
        self.processed_event_service = ProcessedEventService(db)
        self.evidence_service = evidence_service


def _secret_token_provider(settings: Settings, client):
    def provide(uid: str) -> str:
        name = f"projects/{settings.GCP_PROJECT_ID}/secrets/github-token-{uid}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8")

    return provide


def build_context(settings: Settings | None = None) -> WorkerContext:
    settings = settings or get_settings()
    settings.validate_for_role(RuntimeRole.GITHUB_WORKER)
    db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)
    secret_client = secretmanager.SecretManagerServiceClient()
    evidence_service = GitHubEvidenceService(
        httpx.AsyncClient(timeout=15.0),
        _secret_token_provider(settings, secret_client),
    )
    return WorkerContext(settings, db, evidence_service)

def decode_github_event_envelope(data: bytes) -> GitHubEventEnvelope:
    """Validate the publisher's canonical message without key translation."""
    return GitHubEventEnvelope.model_validate_json(data)


async def _send_github_notification(service: TelegramService, chat_id: int, text: str) -> TelegramSendResult:
    """Bridge older test seams while retaining delivery-outcome semantics."""
    send_result = getattr(service, "send_message_result", None)
    if callable(send_result):
        return await send_result(chat_id, text, parse_mode="HTML")
    delivered = await service.send_message(chat_id, text, parse_mode="HTML")
    return TelegramSendResult(delivered=bool(delivered), retryable=not delivered)


async def process_message_async(message: pubsub_v1.subscriber.message.Message, context: WorkerContext):
    """Process a logical GitHub activity without recomputing durable business effects."""
    envelope = None
    claim_acquired = False
    try:
        envelope = decode_github_event_envelope(message.data)
        activity_id = envelope.activityId
        logger.info("Processing GitHub activity %s from delivery %s", activity_id, envelope.deliveryId)

        claim_status = context.processed_event_service.claim(
            activity_id,
            envelope.uid,
            delivery_id=envelope.deliveryId,
        )
        if claim_status is EventClaimStatus.COMPLETED:
            message.ack()
            return
        if claim_status is EventClaimStatus.BUSY:
            message.nack()
            return
        claim_acquired = True

        uid = envelope.uid
        prepared = context.processed_event_service.get_prepared(activity_id, uid)
        if prepared is None:
            try:
                event_context = extract_github_event(envelope)
            except UnsupportedGitHubEvent:
                logger.info("Acknowledging unsupported GitHub event %s", envelope.eventType)
                context.processed_event_service.complete(activity_id, uid)
                message.ack()
                return
            evidence = await context.evidence_service.collect(envelope)
            changes_text = event_context.changesText
            if evidence.text:
                changes_text = f"{changes_text}\n\n--- Code evidence ---\n{evidence.text}"
            from ai.analyzers.github_analyzer import analyze_github_event

            observation_data = await analyze_github_event(
                repo=event_context.repo,
                event_type=event_context.eventType,
                ref=event_context.ref or "",
                commit_count=int(event_context.metadata.get("commitCount", 1)),
                changes_text=changes_text,
            )
            # The production adapter returns this model already. Re-validating here
            # keeps injected test/provider seams from bypassing the persistence boundary.
            from ai.agent import GithubObservationSchema

            if not isinstance(observation_data, GithubObservationSchema):
                raw_analysis = (
                    observation_data
                    if isinstance(observation_data, dict)
                    else vars(observation_data)
                )
                observation_data = GithubObservationSchema.model_validate(raw_analysis)
            prepared = context.processed_event_service.prepare(
                activity_id,
                uid,
                analysis=observation_data.model_dump(),
                event_context={
                    "metadata": {**event_context.metadata, "ref": event_context.ref},
                },
                evidence={
                    "supportsProficiency": evidence.supports_proficiency,
                    "fileCount": evidence.file_count,
                    "truncated": evidence.truncated,
                    "omissionReason": evidence.omission_reason,
                },
            )

        analysis = prepared["analysis"]
        effects = context.processed_event_service.apply_business_effects(activity_id, uid)
        if effects.should_notify and effects.delivery_id and effects.delivery_status == "pending":
            delivery_claim = context.processed_event_service.claim_delivery(
                effects.delivery_id,
                uid,
                effects.decision_id,
            )
            if delivery_claim is DeliveryClaimStatus.ACQUIRED:
                msg = (
                    f"🤖 <b>Mark-I GitHub Analysis</b>\n\n"
                    f"<b>Concept:</b> <code>{html.escape(analysis['concept'])}</code>\n"
                    f"<b>Summary:</b> {html.escape(analysis['summary'])}\n\n"
                    f"<i>(Reason for ping: {html.escape(effects.reason)})</i>"
                )
                delivery_result = await _send_github_notification(context.telegram_service, effects.telegram_chat_id, msg)
                if delivery_result.delivered:
                    context.processed_event_service.mark_delivery(
                        effects.delivery_id,
                        uid,
                        effects.decision_id,
                        "sent",
                    )
                elif delivery_result.ambiguous:
                    context.processed_event_service.mark_delivery(
                        effects.delivery_id,
                        uid,
                        effects.decision_id,
                        "unknown",
                        delivery_result.error,
                    )
                else:
                    context.processed_event_service.mark_delivery(
                        effects.delivery_id,
                        uid,
                        effects.decision_id,
                        "failed",
                        delivery_result.error or "telegram-send-failed",
                    )
                    if delivery_result.retryable:
                        raise RuntimeError("Telegram delivery failed")
            elif delivery_claim is DeliveryClaimStatus.BUSY:
                raise RuntimeError("Telegram delivery lease is busy")
            # UNKNOWN is deliberately terminal for automatic retry: Telegram has no
            # idempotency key, so another automatic send could duplicate a message.

        context.processed_event_service.complete(activity_id, uid)
        logger.info("Processed GitHub activity %s for user %s", activity_id, uid)
        message.ack()

    except Exception as exc:
        if is_terminal_processing_error(exc):
            logger.warning("Acknowledging terminal GitHub event error: %s", type(exc).__name__)
            if envelope is not None and claim_acquired:
                context.processed_event_service.mark_terminal(envelope.activityId, envelope.uid, type(exc).__name__)
            message.ack()
            return
        logger.exception("Retrying GitHub event after recoverable error: %s", type(exc).__name__)
        if envelope is not None and claim_acquired:
            context.processed_event_service.release_for_retry(
                envelope.activityId,
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
