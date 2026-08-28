"""
main.py — Точка входа в приложение.
Именно этот файл мы передаем серверу Uvicorn при запуске (uvicorn app.main:app).
Здесь создается само приложение FastAPI, настраивается защита браузера (CORS) 
и подключаются все роутеры.
"""

from datetime import datetime, timezone

# FastAPI — главный класс, из которого лепится веб-сервер.
# CORSMiddleware — специальный "охранник", который разрешает междоменные запросы.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.dependencies import close_httpx_client

# Импорт наших роутеров v1, webhooks и настроек
from app.api.v1.router import api_v1_router
from app.api.webhooks.github import router as github_webhook_router
from app.api.webhooks.telegram import router as telegram_webhook_router
from telegrambot.bot import setup_webhook
from app.config import RuntimeRole, get_settings
from app.models.common import HealthResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    if settings.ENV == "production":
        settings.validate_for_role(RuntimeRole.API)
    await setup_webhook(settings)
    yield
    # Shutdown
    await close_httpx_client()

# 1. Инициализация (создание) приложения
app = FastAPI(
    title="Mark-I API",
    description="Бэкенд приложения для разработчиков",
    version="1.0.0",
    docs_url="/docs",  # Если зайти на /docs в браузере, FastAPI сам нарисует красивую документацию!
    lifespan=lifespan,
)

# 2. Настройка CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # На всякий случай разрешаем стандартный локальный порт
    ],
    allow_credentials=True,         # Разрешает фронтенду присылать авторизационные токены
    allow_methods=["*"],            # Разрешает любые действия (GET, POST, PATCH)
    allow_headers=["*"],            # Разрешает любые заголовки в запросе
)

# 3. Подключение всех наших роутеров (эндпоинтов) к приложению
app.include_router(api_v1_router)
app.include_router(github_webhook_router, prefix="/api/v1")
app.include_router(telegram_webhook_router, prefix="/api/v1")

# 4. Проверка здоровья (Health Check)
# Это единственный эндпоинт без префикса /api/v1, потому что он технический.
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health Check — это способ проверить, что сервер жив и работает.
    Облачные хостинги (Google Cloud Run) постоянно стучатся сюда. 
    Если сервер отвечает 'ok', значит все хорошо. Если не отвечает, сервер будет перезагружен.
    Здесь нет никакой авторизации (Depends), потому что это публичная информация.
    """
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
    )
