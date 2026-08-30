import logging
import json
import httpx
from datetime import datetime, timezone
from google.cloud.firestore_v1.client import Client as FirestoreClient
from google.cloud import pubsub_v1
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

class OpportunityService:
    def __init__(self, db: FirestoreClient, settings: Settings | None = None, publisher: pubsub_v1.PublisherClient | None = None):
        self._db = db
        settings = settings or get_settings()
        self.publisher = publisher or pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(settings.GCP_PROJECT_ID, "opportunity-collect")

    async def fetch_and_publish_opportunities(self) -> dict:
        """Fetch current articles and publish them for per-user evaluation.

        ``collected_opportunities`` records source ingestion only. It must not
        suppress a later delivery: a user who sets a goal after the first
        collection still needs to be evaluated for an item that remains in the
        source's current window. Per-user worker effects absorb the replay.
        """
        url = "https://dev.to/api/articles?per_page=10"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                articles = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch Dev.to articles: {e}")
            return {"status": "error", "message": str(e)}

        published_count = 0
        for article in articles:
            article_id = str(article.get("id"))
            event_id = f"devto-{article_id}"
            
            collected_ref = self._db.collection("collected_opportunities").document(event_id)
            previous = collected_ref.get()

            # Re-publish items in the source's current window. The worker key
            # is eventId + uid, so this lets newly eligible users be evaluated
            # without repeating existing users' model calls or business writes.
            message_data = {
                "source": "devto",
                "sourceUrl": article.get("url"),
                "sourceName": "Dev.to",
                "title": article.get("title"),
                "description": article.get("description"),
                "tags": article.get("tag_list", []),
                "eventId": event_id
            }
            
            data_bytes = json.dumps(message_data).encode("utf-8")
            try:
                publish_future = self.publisher.publish(self.topic_path, data=data_bytes)
                if hasattr(publish_future, "result"):
                    publish_future.result(timeout=15)
                published_count += 1
                previous_data = previous.to_dict() or {} if previous.exists else {}
                collected_ref.set({
                    "eventId": event_id,
                    "source": "devto",
                    "firstCollectedAt": previous_data.get("firstCollectedAt") or datetime.now(timezone.utc),
                    "lastCollectedAt": datetime.now(timezone.utc),
                })
            except Exception as e:
                logger.error("Failed to publish opportunity %s: %s", event_id, type(e).__name__)
                
        return {"status": "success", "fetched": len(articles), "published": published_count}
