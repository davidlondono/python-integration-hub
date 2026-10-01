import hashlib
import hmac
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from database import SessionLocal
from models import Company, Integration, Job, Sync, WebhookEvent
from schemas import (
    CustomerEventData,
    InvoiceEventData,
    PaymentEventData,
    WebhookAccepted,
    WebhookEnvelope,
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

    return await run_in_threadpool(
        persist_webhook, source, tenant_id, signature, bytes(raw_body)
    )


def persist_webhook(
    source: str, tenant_id: str, signature: str, raw_body: bytes
) -> WebhookAccepted:
    envelope: WebhookEnvelope | None = None
    company_id: UUID | None = None
    try:
        with SessionLocal.begin() as session:
            company = session.scalar(select(Company).where(Company.slug == tenant_id))
            integration = (
                session.scalar(
                    select(Integration).where(
                        Integration.company_id == company.id,
                        Integration.provider == source,
                        Integration.enabled.is_(True),
                    )
                )
                if company
                else None
            )
            secret = integration.config.get("webhook_secret") if integration else None
            if not secret:
                raise HTTPException(
                    status_code=401, detail="Invalid tenant or signature"
                )

            expected_signature = hmac.new(
                secret.encode(), raw_body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_signature, signature):
                raise HTTPException(
                    status_code=401, detail="Invalid tenant or signature"
                )

            try:
                envelope = WebhookEnvelope.model_validate_json(raw_body)
                event_models = {
                    ("crm", "customer.updated"): CustomerEventData,
                    ("billing", "invoice.updated"): InvoiceEventData,
                    ("billing", "payment.updated"): PaymentEventData,
                }
                data = event_models[(source, envelope.type)].model_validate(
                    envelope.data
                )
            except (ValidationError, KeyError) as error:
                raise HTTPException(
                    status_code=422, detail="Invalid webhook event"
                ) from error

            company_id = company.id
            duplicate = _find_existing_sync(session, company.id, source, envelope.id)
            if duplicate:
                return WebhookAccepted(
                    sync_id=str(duplicate.id),
                    status=duplicate.status,
                    duplicate=True,
                )

            event = WebhookEvent(
                id=uuid4(),
                company_id=company.id,
                source=source,
                external_id=envelope.id,
                event_type=envelope.type,
                payload={
                    "id": envelope.id,
                    "type": envelope.type,
                    "data": data.model_dump(),
                },
            )
            sync_id = uuid4()
            sync = Sync(
                id=sync_id,
                company_id=company.id,
                event_id=event.id,
                source=source,
                target="billing" if source == "crm" else "crm",
                entity_type=envelope.type.split(".", maxsplit=1)[0],
                entity_id=data.id,
            )
            session.add(event)
            session.flush()
            session.add(sync)
            session.flush()
            session.add(Job(id=uuid4(), company_id=company.id, sync_id=sync_id))
    except IntegrityError:
        if company_id is not None and envelope is not None:
            with SessionLocal() as session:
                duplicate = _find_existing_sync(
                    session, company_id, source, envelope.id
                )
                if duplicate:
                    return WebhookAccepted(
                        sync_id=str(duplicate.id),
                        status=duplicate.status,
                        duplicate=True,
                    )
        raise

    return WebhookAccepted(sync_id=str(sync_id), status="pending")


def _find_existing_sync(
    session: Session, company_id: UUID, source: str, external_id: str
) -> Sync | None:
    return session.scalar(
        select(Sync)
        .join(WebhookEvent, Sync.event_id == WebhookEvent.id)
        .where(
            Sync.company_id == company_id,
            WebhookEvent.source == source,
            WebhookEvent.external_id == external_id,
        )
    )
