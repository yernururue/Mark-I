import os
import httpx
import logging

logger = logging.getLogger(__name__)

async def setup_webhook():
    """
    Called on startup to register the webhook URL with Telegram.
    For this to work, BACKEND_URL or something similar must be defined.
    If it's local dev, you might skip this or use ngrok.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL")
    
    if not bot_token or not webhook_url:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_URL missing, skipping webhook setup.")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram webhook set successfully.")
            else:
                logger.error(f"Failed to set webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
