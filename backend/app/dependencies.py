"""
dependencies.py — Глобальные подключения (база данных, GCP сервисы, HTTP клиент).
"""

from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import httpx
from google.cloud import pubsub_v1, secretmanager
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.config import settings
from app.services.github_service import GitHubService


def _initialize_firebase() -> None:
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

    _initialize_firebase()

    if _firestore_client is None:
        _firestore_client = firestore.client(
            app=firebase_admin.get_app(),
            database_id=settings.FIRESTORE_DATABASE,
        )

    return _firestore_client


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


from fastapi import Depends
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
        settings=settings,
    )
