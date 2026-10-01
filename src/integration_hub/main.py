from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from integration_hub.schemas import SyncStatus, WebhookAccepted
from integration_hub.services.syncs import get_sync, list_syncs
from integration_hub.services.webhooks import (
    InvalidWebhookEvent,
    InvalidWebhookSignature,
    persist_webhook,
)

app = FastAPI(title="Integration Hub")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/{source}", status_code=202, response_model=WebhookAccepted)
async def receive_webhook(
    source: Literal["crm", "billing"],
    request: Request,
    tenant_id: Annotated[
        str, Header(alias="X-Tenant-ID", min_length=1, max_length=100)
    ],
    signature: Annotated[
        str, Header(alias="X-Signature-SHA256", min_length=64, max_length=64)
    ],
) -> WebhookAccepted:
    raw_body = bytearray()
    async for chunk in request.stream():
        if len(raw_body) + len(chunk) > 1_048_576:
            raise HTTPException(status_code=413, detail="Webhook payload is too large")
        raw_body.extend(chunk)

    try:
        return await run_in_threadpool(
            persist_webhook, source, tenant_id, signature, bytes(raw_body)
        )
    except InvalidWebhookSignature as error:
        raise HTTPException(
            status_code=401, detail="Invalid tenant or signature"
        ) from error
    except InvalidWebhookEvent as error:
        raise HTTPException(status_code=422, detail="Invalid webhook event") from error


@app.get("/syncs", response_model=list[SyncStatus])
def get_syncs(
    tenant_id: Annotated[
        str, Header(alias="X-Tenant-ID", min_length=1, max_length=100)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[SyncStatus]:
    syncs = list_syncs(tenant_id, limit)
    if syncs is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return syncs


@app.get("/syncs/{sync_id}", response_model=SyncStatus)
def get_sync_status(
    sync_id: UUID,
    tenant_id: Annotated[
        str, Header(alias="X-Tenant-ID", min_length=1, max_length=100)
    ],
) -> SyncStatus:
    sync = get_sync(tenant_id, sync_id)
    if sync is None:
        raise HTTPException(status_code=404, detail="Sync not found")
    return sync
