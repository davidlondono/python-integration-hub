import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from integration_hub.database import SessionLocal
from integration_hub.main import app
from integration_hub.models import Job, Sync

client = TestClient(app)


def test_sync_status_is_visible_only_to_owning_tenant() -> None:
    body = json.dumps(
        {
            "id": f"evt-{uuid4()}",
            "type": "customer.updated",
            "data": {
                "id": f"customer-{uuid4()}",
                "name": "Ada Lovelace",
                "email": "ada@example.test",
            },
        }
    ).encode()
    signature = hmac.new(b"demo-acme-crm-secret", body, hashlib.sha256).hexdigest()
    response = client.post(
        "/webhooks/crm",
        content=body,
        headers={
            "X-Tenant-ID": "acme",
            "X-Signature-SHA256": signature,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    sync_id = UUID(response.json()["sync_id"])
    with SessionLocal.begin() as session:
        job = session.scalar(select(Job).where(Job.sync_id == sync_id))
        job.available_at = datetime.now(UTC) + timedelta(hours=1)

    headers = {"X-Tenant-ID": "acme"}
    listed = client.get("/syncs", headers=headers)
    detail = client.get(f"/syncs/{sync_id}", headers=headers)
    assert listed.status_code == detail.status_code == 200
    assert listed.json()[0]["id"] == str(sync_id)
    assert detail.json()["status"] == "pending"

    with SessionLocal.begin() as session:
        session.get(Sync, sync_id).status = "processing"
        session.scalar(select(Job).where(Job.sync_id == sync_id)).status = "processing"
    assert client.get(f"/syncs/{sync_id}", headers=headers).json()["status"] == (
        "processing"
    )

    assert (
        client.get(f"/syncs/{sync_id}", headers={"X-Tenant-ID": "globex"}).status_code
        == 404
    )
    assert client.get("/syncs", headers={"X-Tenant-ID": "globex"}).json() == []
