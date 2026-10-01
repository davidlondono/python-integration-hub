import hashlib
import hmac
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from connectors import get_billing_customer, get_crm_invoice, get_crm_payment
from database import SessionLocal
from main import app
from models import Job, Sync
from worker import process_job

client = TestClient(app)


@pytest.mark.parametrize(
    ("source", "event_type", "data"),
    [
        (
            "crm",
            "customer.updated",
            {
                "id": f"customer-{uuid4()}",
                "name": "Ada Lovelace",
                "email": "ada@example.test",
            },
        ),
        (
            "billing",
            "invoice.updated",
            {
                "id": f"invoice-{uuid4()}",
                "customer_id": "customer_001",
                "amount_minor": 12500,
                "currency": "USD",
                "status": "open",
            },
        ),
        (
            "billing",
            "payment.updated",
            {
                "id": f"payment-{uuid4()}",
                "invoice_id": "invoice_001",
                "amount_minor": 12500,
                "currency": "USD",
                "status": "paid",
            },
        ),
    ],
)
def test_worker_delivers_supported_entities(
    source: str, event_type: str, data: dict[str, object]
) -> None:
    body = json.dumps(
        {"id": f"evt-{uuid4()}", "type": event_type, "data": data}
    ).encode()
    secret = f"demo-acme-{source}-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    response = client.post(
        f"/webhooks/{source}",
        content=body,
        headers={
            "X-Tenant-ID": "acme",
            "X-Signature-SHA256": signature,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202

    with SessionLocal() as session:
        sync_id = UUID(response.json()["sync_id"])
        sync = session.get(Sync, sync_id)
        assert sync is not None
        job_id = session.scalar(select(Job.id).where(Job.sync_id == sync.id))
    assert job_id is not None

    assert process_job(job_id)

    if event_type == "customer.updated":
        assert get_billing_customer("acme", str(data["id"])) == data
    elif event_type == "invoice.updated":
        assert get_crm_invoice("acme", str(data["id"])) == data
    else:
        assert get_crm_payment("acme", str(data["id"])) == data

    with SessionLocal() as session:
        assert session.get(Job, job_id).status == "succeeded"
        assert session.get(Sync, sync_id).status == "succeeded"
