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
        """
        Fetches recent articles from Dev.to API, checks for duplicates,
        and publishes new ones to Pub/Sub for evaluation.
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
            
            # Check if we already processed this article globally
            # In a real app we might have a global 'processed_opportunities' or just 'processed_events' without userId
            doc_ref = self._db.collection("processed_events").document(event_id)
            if doc_ref.get().exists:
                continue
                
            # If new, we publish it to Pub/Sub
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
                self.publisher.publish(self.topic_path, data=data_bytes)
                published_count += 1
                
                # Mark as processed so we don't fetch it again next time
                doc_ref.set({
                    "eventId": event_id,
                    "source": "devto",
                    "processedAt": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.error(f"Failed to publish opportunity {event_id}: {e}")
                
        return {"status": "success", "fetched": len(articles), "published": published_count}
