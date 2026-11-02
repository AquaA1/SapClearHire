"""Add interview_transcripts and transcript_qa_items tables for Phase 3 Interview Coach

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-03 02:08:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create interview_transcripts table
    op.create_table(
        "interview_transcripts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploader_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("round_name", sa.String(120), nullable=False, server_default="Technical Interview"),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False, server_default="text/plain"),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("processing_error", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_interview_transcripts_app_id", "interview_transcripts", ["application_id"])
    op.create_index("ix_interview_transcripts_uploader_id", "interview_transcripts", ["uploader_id"])
    op.create_index("ix_interview_transcripts_file_hash", "interview_transcripts", ["file_hash"])
    op.create_index("ix_interview_transcripts_status", "interview_transcripts", ["processing_status"])

    # 2. Create transcript_qa_items table
    op.create_table(
        "transcript_qa_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("transcript_id", sa.Uuid(as_uuid=True), sa.ForeignKey("interview_transcripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("interviewer_question", sa.Text(), nullable=False),
        sa.Column("candidate_answer_excerpt", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("mapped_criterion_id", sa.Uuid(as_uuid=True), sa.ForeignKey("job_criteria.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mapped_skill_name", sa.String(150), nullable=True),
        sa.Column("evidence_status", sa.String(50), nullable=False, server_default="supported"),
        sa.Column("expected_concept", sa.Text(), nullable=False),
        sa.Column("alignment_summary", sa.Text(), nullable=False),
        sa.Column("coaching_suggestion", sa.Text(), nullable=False),
        sa.Column("clarification_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("candidate_clarification_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transcript_qa_items_transcript_id", "transcript_qa_items", ["transcript_id"])
    op.create_index("ix_transcript_qa_items_criterion_id", "transcript_qa_items", ["mapped_criterion_id"])


def downgrade() -> None:
    op.drop_index("ix_transcript_qa_items_criterion_id", table_name="transcript_qa_items")
    op.drop_index("ix_transcript_qa_items_transcript_id", table_name="transcript_qa_items")
    op.drop_table("transcript_qa_items")

    op.drop_index("ix_interview_transcripts_status", table_name="interview_transcripts")
    op.drop_index("ix_interview_transcripts_file_hash", table_name="interview_transcripts")
    op.drop_index("ix_interview_transcripts_uploader_id", table_name="interview_transcripts")
    op.drop_index("ix_interview_transcripts_app_id", table_name="interview_transcripts")
    op.drop_table("interview_transcripts")
