"""add job lease timestamp

Revision ID: 8c5a1d34ee2f
Revises: 0f43bd7c4a11
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c5a1d34ee2f"
down_revision: str | None = "0f43bd7c4a11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("locked_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("jobs", "locked_at")
