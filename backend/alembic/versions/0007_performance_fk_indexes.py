"""Add performance foreign key and composite indexes on applications, evaluations, reviews, and jobs

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-03 01:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Applications query optimization (job_id, status)
    op.create_index(
        "ix_applications_job_status",
        "applications",
        ["job_id", "status"],
        unique=False,
    )
    # 2. Criterion evidence lookup by evaluation
    op.create_index(
        "ix_criterion_evidence_evaluation_id",
        "criterion_evidence",
        ["evaluation_id"],
        unique=False,
    )
    # 3. Review decisions lookup by criterion evidence
    op.create_index(
        "ix_review_decisions_ce_id",
        "review_decisions",
        ["criterion_evidence_id"],
        unique=False,
    )
    # 4. Correction requests lookup by criterion evidence
    op.create_index(
        "ix_correction_requests_ce_id",
        "correction_requests",
        ["criterion_evidence_id"],
        unique=False,
    )
    # 5. Jobs query optimization by employer and status
    op.create_index(
        "ix_jobs_employer_status",
        "jobs",
        ["employer_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_employer_status", table_name="jobs")
    op.drop_index("ix_correction_requests_ce_id", table_name="correction_requests")
    op.drop_index("ix_review_decisions_ce_id", table_name="review_decisions")
    op.drop_index("ix_criterion_evidence_evaluation_id", table_name="criterion_evidence")
    op.drop_index("ix_applications_job_status", table_name="applications")
