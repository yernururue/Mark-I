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
    secret_token = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    
    if not bot_token or not webhook_url:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_URL missing, skipping webhook setup.")
        return
        
    info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    set_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    payload = {"url": webhook_url}
    if secret_token:
        payload["secret_token"] = secret_token
    
    try:
        async with httpx.AsyncClient() as client:
            # Check if it's already set to the correct URL
            info_resp = await client.get(info_url)
            if info_resp.status_code == 200:
                data = info_resp.json()
                if data.get("result", {}).get("url") == webhook_url:
                    logger.info("Telegram webhook is already set to the correct URL.")
                    return
            
            # Set the webhook
            response = await client.post(set_url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram webhook set successfully.")
            else:
                logger.error(f"Failed to set webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
