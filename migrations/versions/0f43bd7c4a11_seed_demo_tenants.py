"""seed local demo tenants

Revision ID: 0f43bd7c4a11
Revises: e6b9a0973ea4
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0f43bd7c4a11"
down_revision: str | None = "e6b9a0973ea4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACME_ID = "00000000-0000-4000-8000-000000000001"
GLOBEX_ID = "00000000-0000-4000-8000-000000000002"


def upgrade() -> None:
    companies = sa.table(
        "companies",
        sa.column("id", sa.Uuid()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
    )
    integrations = sa.table(
        "integrations",
        sa.column("id", sa.Uuid()),
        sa.column("company_id", sa.Uuid()),
        sa.column("provider", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("config", postgresql.JSONB()),
    )
    op.bulk_insert(
        companies,
        [
            {"id": ACME_ID, "slug": "acme", "name": "Acme Demo"},
            {"id": GLOBEX_ID, "slug": "globex", "name": "Globex Demo"},
        ],
    )
    op.bulk_insert(
        integrations,
        [
            {
                "id": "00000000-0000-4000-8000-000000000101",
                "company_id": ACME_ID,
                "provider": "crm",
                "enabled": True,
                "config": {"webhook_secret": "demo-acme-crm-secret"},
            },
            {
                "id": "00000000-0000-4000-8000-000000000102",
                "company_id": ACME_ID,
                "provider": "billing",
                "enabled": True,
                "config": {"webhook_secret": "demo-acme-billing-secret"},
            },
            {
                "id": "00000000-0000-4000-8000-000000000201",
                "company_id": GLOBEX_ID,
                "provider": "crm",
                "enabled": True,
                "config": {"webhook_secret": "demo-globex-crm-secret"},
            },
            {
                "id": "00000000-0000-4000-8000-000000000202",
                "company_id": GLOBEX_ID,
                "provider": "billing",
                "enabled": True,
                "config": {"webhook_secret": "demo-globex-billing-secret"},
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM integrations WHERE company_id IN (:acme, :globex)"
        ).bindparams(acme=ACME_ID, globex=GLOBEX_ID)
    )
    op.execute(
        sa.text("DELETE FROM companies WHERE id IN (:acme, :globex)").bindparams(
            acme=ACME_ID, globex=GLOBEX_ID
        )
    )
