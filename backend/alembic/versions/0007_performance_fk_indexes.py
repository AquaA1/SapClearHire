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


def _create_index_if_not_exists(name: str, table_name: str, columns: list) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indexes = [idx["name"] for idx in insp.get_indexes(table_name)]
    if name not in indexes:
        op.create_index(name, table_name, columns, unique=False)


def upgrade() -> None:
    # 1. Applications query optimization (job_id, status)
    _create_index_if_not_exists("ix_applications_job_status", "applications", ["job_id", "status"])
    # 2. Criterion evidence lookup by evaluation
    _create_index_if_not_exists("ix_criterion_evidence_evaluation_id", "criterion_evidence", ["evaluation_id"])
    # 3. Review decisions lookup by criterion evidence
    _create_index_if_not_exists("ix_review_decisions_ce_id", "review_decisions", ["criterion_evidence_id"])
    # 4. Correction requests lookup by criterion evidence
    _create_index_if_not_exists("ix_correction_requests_ce_id", "correction_requests", ["criterion_evidence_id"])
    # 5. Jobs query optimization by employer and status
    _create_index_if_not_exists("ix_jobs_employer_status", "jobs", ["employer_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_employer_status", table_name="jobs")
    op.drop_index("ix_correction_requests_ce_id", table_name="correction_requests")
    op.drop_index("ix_review_decisions_ce_id", table_name="review_decisions")
    op.drop_index("ix_criterion_evidence_evaluation_id", table_name="criterion_evidence")
    op.drop_index("ix_applications_job_status", table_name="applications")
