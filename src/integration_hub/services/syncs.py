from uuid import UUID

from sqlalchemy import select

from integration_hub.database import SessionLocal
from integration_hub.models import Company, Sync


def list_syncs(tenant_id: str, limit: int) -> list[Sync] | None:
    with SessionLocal() as session:
        company_id = session.scalar(select(Company.id).where(Company.slug == tenant_id))
        if company_id is None:
            return None
        return list(
            session.scalars(
                select(Sync)
                .where(Sync.company_id == company_id)
                .order_by(Sync.created_at.desc())
                .limit(limit)
            )
        )


def get_sync(tenant_id: str, sync_id: UUID) -> Sync | None:
    with SessionLocal() as session:
        company_id = session.scalar(select(Company.id).where(Company.slug == tenant_id))
        if company_id is None:
            return None
        return session.scalar(
            select(Sync).where(Sync.id == sync_id, Sync.company_id == company_id)
        )
