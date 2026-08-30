from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from app.worker_apps import _create_worker_app


def _push_body(data: bytes) -> dict:
    return {"message": {"data": base64.b64encode(data).decode("ascii")}}


def test_private_push_adapter_passes_decoded_bytes_to_worker_and_acks_with_204():
    contexts: list[object] = []

    def context_factory():
        context = object()
        contexts.append(context)
        return context

    async def process(message, context):
        assert context is contexts[0]
        assert message.data == b'{"deliveryId":"d-1"}'
        message.ack()

    app = _create_worker_app(title="test", context_factory=context_factory, process=process)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/", json=_push_body(b'{"deliveryId":"d-1"}'))

    assert response.status_code == 204
    assert len(contexts) == 1


def test_push_adapter_uses_503_for_worker_nack_and_400_for_invalid_envelope():
    async def nack(message, context):
        del context
        message.nack()

    app = _create_worker_app(title="test", context_factory=object, process=nack)
    with TestClient(app, raise_server_exceptions=False) as client:
        retry = client.post("/", json=_push_body(b"event"))
        invalid = client.post("/", json={"message": {"data": "not-base64!"}})

    assert retry.status_code == 503
    assert invalid.status_code == 400
