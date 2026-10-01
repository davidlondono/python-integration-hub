from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=100)
    data: dict[str, object]


class CustomerEventData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)


class InvoiceEventData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    customer_id: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern="^[A-Z]{3}$")
    status: Literal["draft", "open", "paid", "void"]


class PaymentEventData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    invoice_id: str = Field(min_length=1, max_length=200)
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern="^[A-Z]{3}$")
    status: Literal["pending", "paid", "failed", "refunded"]


class WebhookAccepted(BaseModel):
    sync_id: str
    status: Literal["pending", "processing", "retrying", "succeeded", "dead_letter"]
    duplicate: bool = False


class SyncStatus(BaseModel):
    id: UUID
    source: str
    target: str
    entity_type: str
    entity_id: str
    status: Literal["pending", "processing", "retrying", "succeeded", "dead_letter"]
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime
