"""Add performance composite indexes on applications, jobs, and evaluations

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-01 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_applications_candidate_created_at",
        "applications",
        ["candidate_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_jobs_status_created_at",
        "jobs",
        ["status", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_evaluations_app_latest",
        "evaluations",
        ["application_id", "is_latest"],
    )


def downgrade() -> None:
    op.drop_index("ix_evaluations_app_latest", table_name="evaluations")
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_index("ix_applications_candidate_created_at", table_name="applications")
