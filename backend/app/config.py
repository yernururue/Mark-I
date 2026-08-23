import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Google Cloud
    GCP_PROJECT_ID: str = Field(..., env="GCP_PROJECT_ID")
    FIRESTORE_DATABASE: str = Field("mark-i", env="FIRESTORE_DATABASE")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")

    # Gemini
    GEMINI_MODEL: str = Field("gemini-3.5-flash", env="GEMINI_MODEL")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_USERNAME: str = Field(..., env="TELEGRAM_BOT_USERNAME")

    # GitHub
    GITHUB_CLIENT_ID: str = Field(..., env="GITHUB_CLIENT_ID")
    # For local development we can read secrets directly from env.
    # On Cloud Run, we can map Secret Manager values to environment variables.
    GITHUB_CLIENT_SECRET: str = Field(..., env="GITHUB_CLIENT_SECRET")
    GITHUB_WEBHOOK_SECRET: str = Field(..., env="GITHUB_WEBHOOK_SECRET")

    @field_validator('GITHUB_WEBHOOK_SECRET')
    @classmethod
    def secret_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('GITHUB_WEBHOOK_SECRET cannot be empty')
        return v

    # Pub/Sub Topics
    PUBSUB_GITHUB_TOPIC: str = Field("github-events", env="PUBSUB_GITHUB_TOPIC")
    PUBSUB_OPPORTUNITY_TOPIC: str = Field("opportunity-collect", env="PUBSUB_OPPORTUNITY_TOPIC")

    # Webhook Base URL (used for registering GitHub webhooks)
    WEBHOOK_BASE_URL: Optional[str] = Field(None, env="WEBHOOK_BASE_URL")

    # Frontend
    FRONTEND_URL: str = Field("http://localhost:3000", env="FRONTEND_URL")

    # App environment (e.g. "development", "production")
    ENV: str = Field("development", env="ENV")

    model_config = SettingsConfigDict(
        # Look for .env in current directory and parent directory
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )



# Create settings instance
settings = Settings()
