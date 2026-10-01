import hashlib
import hmac
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from main import app
from models import Job, Sync, WebhookEvent

client = TestClient(app)


def _signed_headers(tenant_id: str, source: str, body: bytes) -> dict[str, str]:
    secret = f"demo-{tenant_id}-{source}-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Tenant-ID": tenant_id,
        "X-Signature-SHA256": signature,
        "Content-Type": "application/json",
    }


def test_webhook_rejects_invalid_signature() -> None:
    body = json.dumps(
        {
            "id": f"evt-{uuid4()}",
            "type": "customer.updated",
            "data": {
                "id": "customer_001",
                "name": "Ada Lovelace",
                "email": "ada@example.test",
            },
        }
    ).encode()

    response = client.post(
        "/webhooks/crm",
        content=body,
        headers={
            "X-Tenant-ID": "acme",
            "X-Signature-SHA256": "0" * 64,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401


def test_signed_webhook_persists_event_sync_and_job() -> None:
    event_id = f"evt-{uuid4()}"
    body = json.dumps(
        {
            "id": event_id,
            "type": "customer.updated",
            "data": {
                "id": "customer_001",
                "name": "Ada Lovelace",
                "email": "ada@example.test",
            },
        }
    ).encode()
    response = client.post(
        "/webhooks/crm",
        content=body,
        headers=_signed_headers("acme", "crm", body),
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    with SessionLocal() as session:
        event = session.scalar(
            select(WebhookEvent).where(WebhookEvent.external_id == event_id)
        )
        assert event is not None
        sync = session.scalar(select(Sync).where(Sync.event_id == event.id))
        assert sync is not None
        assert sync.company_id == event.company_id
        job = session.scalar(select(Job).where(Job.sync_id == sync.id))
        assert job is not None


def test_webhook_rejects_invalid_event_data() -> None:
    body = json.dumps(
        {
            "id": f"evt-{uuid4()}",
            "type": "customer.updated",
            "data": {"id": "customer_001", "name": "", "email": "x"},
        }
    ).encode()

    response = client.post(
        "/webhooks/crm",
        content=body,
        headers=_signed_headers("acme", "crm", body),
    )

    assert response.status_code == 422


def test_webhook_rejects_oversized_body() -> None:
    response = client.post(
        "/webhooks/crm",
        content=b"x" * (1_048_576 + 1),
        headers={
            "X-Tenant-ID": "acme",
            "X-Signature-SHA256": "0" * 64,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 413
