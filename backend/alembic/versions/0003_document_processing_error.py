"""Add processing_error to documents

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29 23:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("processing_error", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "processing_error")
