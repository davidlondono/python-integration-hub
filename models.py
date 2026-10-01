from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("company_id", "provider"),
        CheckConstraint("provider IN ('crm', 'billing')"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("company_id", "source", "external_id"),
        UniqueConstraint("company_id", "id"),
        CheckConstraint("source IN ('crm', 'billing')"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Sync(Base):
    __tablename__ = "syncs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "event_id"],
            ["webhook_events.company_id", "webhook_events.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "event_id"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'retrying', 'succeeded', 'dead_letter')"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(Uuid)
    event_id: Mapped[UUID] = mapped_column(Uuid)
    source: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "sync_id"],
            ["syncs.company_id", "syncs.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("company_id", "sync_id"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'retrying', 'succeeded', 'dead_letter')"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    company_id: Mapped[UUID] = mapped_column(Uuid)
    sync_id: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
