"""
main.py — Точка входа в приложение.
Именно этот файл мы передаем серверу Uvicorn при запуске (uvicorn app.main:app).
Здесь создается само приложение FastAPI, настраивается защита браузера (CORS) 
и подключаются все роутеры.
"""

from datetime import datetime, timezone

# FastAPI — главный класс, из которого лепится веб-сервер.
# CORSMiddleware — специальный "охранник", который разрешает междоменные запросы.
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from app.dependencies import close_httpx_client

# Импорт наших роутеров v1, webhooks и настроек
from app.api.v1.router import api_v1_router
from app.api.webhooks.github import router as github_webhook_router
from app.api.webhooks.telegram import router as telegram_webhook_router
from telegrambot.bot import setup_webhook
from app.config import RuntimeRole, get_settings
from app.errors import DomainError
from app.models.common import ErrorResponse, HealthResponse

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    frontend_origin = get_settings().FRONTEND_URL.rstrip("/")
    if frontend_origin and frontend_origin not in origins:
        origins.append(frontend_origin)
    return origins


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    settings.validate_for_role(RuntimeRole.API)
    await setup_webhook(settings)
    yield
    # Shutdown
    await close_httpx_client()

# 1. Инициализация (создание) приложения
app = FastAPI(
    title="Mark-I API",
    description="AI-powered developer growth agent REST API.",
    version="1.0.0",
    docs_url="/docs",  # Если зайти на /docs в браузере, FastAPI сам нарисует красивую документацию!
    lifespan=lifespan,
    responses={422: {"model": ErrorResponse, "description": "Invalid request"}},
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "; ".join(error.get("msg", "Invalid request") for error in exc.errors())
    return _error_response(422, "VALIDATION_ERROR", message)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("error"), dict):
        error = detail["error"]
        return _error_response(exc.status_code, error.get("code", "HTTP_ERROR"), error.get("message", "Request failed"))
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    response = _error_response(exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=exc)
    return _error_response(500, "INTERNAL_ERROR", "Internal server error")

# 2. Настройка CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
@app.get("/health", response_model=HealthResponse, tags=["Health"], operation_id="healthCheck")
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
