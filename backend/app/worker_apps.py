"""Private HTTP adapters for Pub/Sub push delivery on Cloud Run.

The worker domain code remains transport-agnostic and can also run a pull
subscriber outside Cloud Run. Cloud Run services, however, must listen on the
injected port, so production deploys use these authenticated Pub/Sub push
adapters instead of an idle pull loop.
"""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, Response, status

from workers import github_worker, opportunity_worker


class _PushMessage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = False
        self.nacked = False

    def ack(self) -> None:
        self.acked = True

    def nack(self) -> None:
        self.nacked = True


async def _decode_push_data(request: Request) -> bytes:
    try:
        body = await request.json()
        encoded = body["message"]["data"]
        if not isinstance(encoded, str):
            raise TypeError("message.data is not a string")
        return base64.b64decode(encoded, validate=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Pub/Sub push envelope") from exc


def _create_worker_app(
    *,
    title: str,
    context_factory: Callable[[], Any],
    process: Callable[[Any, Any], Any],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.context = context_factory()
        yield

    app = FastAPI(title=title, docs_url=None, redoc_url=None, lifespan=lifespan)

    @app.get("/health", status_code=status.HTTP_200_OK)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/", status_code=status.HTTP_204_NO_CONTENT)
    async def receive_push(request: Request) -> Response:
        message = _PushMessage(await _decode_push_data(request))
        await process(message, request.app.state.context)
        # Returning a non-2xx tells Pub/Sub to redeliver. Business code makes
        # this decision through ack/nack rather than through transport details.
        if message.nacked or not message.acked:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Retry Pub/Sub delivery")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


github_app = _create_worker_app(
    title="Mark-I GitHub Worker",
    context_factory=github_worker.build_context,
    process=github_worker.process_message_async,
)
opportunity_app = _create_worker_app(
    title="Mark-I Opportunity Worker",
    context_factory=opportunity_worker.build_context,
    process=opportunity_worker.process_message_async,
)
