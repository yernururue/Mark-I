"""
dependencies.py — Глобальные подключения (база данных, GCP сервисы, HTTP клиент).
"""

from typing import Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore
import httpx
from google.cloud import pubsub_v1, secretmanager
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.config import Settings, get_settings
from fastapi import Depends, HTTPException

from app.middleware.auth import get_current_user
from app.services.chat_service import ChatService
from app.services.dashboard_service import DashboardService
from app.services.decision_service import DecisionService
from app.services.github_service import GitHubService
from app.services.observation_service import ObservationService
from app.services.opportunity_service import OpportunityService
from app.services.skill_service import SkillService
from app.services.telegram_service import TelegramService
from app.services.user_service import UserService


def _initialize_firebase(settings: Settings) -> None:
    """Подключение к сервисам Google (Firebase)."""
    if firebase_admin._apps:
        return

    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        "projectId": settings.GCP_PROJECT_ID,
    })


_firestore_client: Optional[FirestoreClient] = None
_httpx_client: Optional[httpx.AsyncClient] = None
_pubsub_publisher: Optional[pubsub_v1.PublisherClient] = None
_secret_client: Optional[secretmanager.SecretManagerServiceClient] = None


def get_firestore_client() -> FirestoreClient:
    """Функция, которая выдает подключение к базе данных Firestore (Singleton)."""
    global _firestore_client

    settings = get_settings()
    _initialize_firebase(settings)

    if _firestore_client is None:
        _firestore_client = firestore.client(
            app=firebase_admin.get_app(),
            database_id=settings.FIRESTORE_DATABASE,
        )

    return _firestore_client


def get_db() -> FirestoreClient:
    """Canonical Firestore dependency, intentionally override-friendly in tests."""
    return get_firestore_client()


async def get_current_user_id(current_user: dict[str, Any] = Depends(get_current_user)) -> str:
    """Return only the verified Firebase UID required by most routes."""
    uid = current_user.get("uid")
    if not isinstance(uid, str) or not uid:
        raise HTTPException(status_code=401, detail="Authenticated token does not contain uid")
    return uid


def get_httpx_client() -> httpx.AsyncClient:
    """Функция, которая выдает асинхронный HTTP клиент (Singleton)."""
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=15.0)
    return _httpx_client


async def close_httpx_client() -> None:
    """Закрывает асинхронный HTTP клиент."""
    global _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
        _httpx_client = None


def get_pubsub_publisher() -> pubsub_v1.PublisherClient:
    """Функция, которая выдает клиент Google Pub/Sub Publisher (Singleton)."""
    global _pubsub_publisher
    if _pubsub_publisher is None:
        _pubsub_publisher = pubsub_v1.PublisherClient()
    return _pubsub_publisher


def get_secret_client() -> secretmanager.SecretManagerServiceClient:
    """Функция, которая выдает клиент GCP Secret Manager (Singleton)."""
    global _secret_client
    if _secret_client is None:
        _secret_client = secretmanager.SecretManagerServiceClient()
    return _secret_client


def get_github_service(
    db: FirestoreClient = Depends(get_firestore_client),
    httpx_client: httpx.AsyncClient = Depends(get_httpx_client),
    secret_client: secretmanager.SecretManagerServiceClient = Depends(get_secret_client),
    pubsub_publisher: pubsub_v1.PublisherClient = Depends(get_pubsub_publisher),
) -> GitHubService:
    """Функция, которая выдает сервис GitHub (DI Factory)."""
    return GitHubService(
        db=db,
        httpx_client=httpx_client,
        secret_client=secret_client,
        pubsub_publisher=pubsub_publisher,
        settings=get_settings(),
    )


def get_user_service(db: FirestoreClient = Depends(get_db)) -> UserService:
    return UserService(db)


def get_chat_service(db: FirestoreClient = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_dashboard_service(db: FirestoreClient = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


def get_skill_service(db: FirestoreClient = Depends(get_db)) -> SkillService:
    return SkillService(db)


def get_observation_service(db: FirestoreClient = Depends(get_db)) -> ObservationService:
    return ObservationService(db)


def get_telegram_service(db: FirestoreClient = Depends(get_db)) -> TelegramService:
    return TelegramService(db)


def get_decision_service(db: FirestoreClient = Depends(get_db)) -> DecisionService:
    return DecisionService(db)


def get_opportunity_service(db: FirestoreClient = Depends(get_db)) -> OpportunityService:
    return OpportunityService(db)
