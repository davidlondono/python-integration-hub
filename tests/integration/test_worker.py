import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from integration_hub import worker
from integration_hub.connectors.simulated import (
    get_billing_customer,
    get_crm_invoice,
    get_crm_payment,
)
from integration_hub.database import SessionLocal
from integration_hub.main import app
from integration_hub.models import Job, Sync
from integration_hub.services import delivery
from integration_hub.worker import process_job

client = TestClient(app)


def _enqueue_job(source: str, event_type: str, data: dict[str, object]) -> UUID:
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
        sync = session.get(Sync, UUID(response.json()["sync_id"]))
        job_id = session.scalar(select(Job.id).where(Job.sync_id == sync.id))
    assert job_id is not None
    return job_id


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
    job_id = _enqueue_job(source, event_type, data)
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        sync_id = job.sync_id

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


def test_worker_retries_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = _enqueue_job(
        "crm",
        "customer.updated",
        {"id": f"customer-{uuid4()}", "name": "Ada", "email": "ada@example.test"},
    )
    deliver = delivery.deliver_event
    calls = 0

    def fail_once(*args: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("temporary")
        deliver(*args)

    monkeypatch.setattr(delivery, "deliver_event", fail_once)
    assert process_job(job_id)
    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        sync = session.get(Sync, job.sync_id)
        sync_id = sync.id
        assert job.status == sync.status == "retrying"
        assert job.attempts == sync.attempts == 1
        assert job.last_error == sync.last_error == "ConnectionError"
        assert job.available_at > datetime.now(UTC)
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)

    assert process_job(job_id)
    with SessionLocal() as session:
        assert session.get(Job, job_id).status == "succeeded"
        assert session.get(Sync, sync_id).status == "succeeded"
        assert session.get(Job, job_id).attempts == 2


def test_worker_dead_letters_after_five_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = _enqueue_job(
        "crm",
        "customer.updated",
        {"id": f"customer-{uuid4()}", "name": "Ada", "email": "ada@example.test"},
    )

    def always_fail(*_args: object) -> None:
        raise ConnectionError

    monkeypatch.setattr(delivery, "deliver_event", always_fail)

    for attempt in range(1, worker.MAX_ATTEMPTS + 1):
        if attempt > 1:
            with SessionLocal.begin() as session:
                job = session.get(Job, job_id)
                job.available_at = datetime.now(UTC) - timedelta(seconds=1)
        assert process_job(job_id)
        with SessionLocal() as session:
            job = session.get(Job, job_id)
            sync = session.get(Sync, job.sync_id)
            expected_status = (
                "dead_letter" if attempt == worker.MAX_ATTEMPTS else "retrying"
            )
            assert job.status == sync.status == expected_status
            assert job.attempts == sync.attempts == attempt
            assert job.last_error == sync.last_error == "ConnectionError"
