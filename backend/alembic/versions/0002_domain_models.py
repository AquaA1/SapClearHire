"""Add ClearHire Phase 1 domain models

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("employer_id", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_employer_id"), "users", ["employer_id"], unique=False)

    # 2. documents
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text_by_page", sa.JSON(), nullable=False),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["users.id"],
            name=op.f("fk_documents_candidate_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_candidate_id"), "documents", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_documents_file_hash"), "documents", ["file_hash"], unique=False)
    op.create_index(
        op.f("ix_documents_processing_status"), "documents", ["processing_status"], unique=False
    )

    # 3. extraction_runs
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_extraction_runs_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extraction_runs")),
        sa.UniqueConstraint("document_id", "run_number", name="uq_extraction_runs_doc_run"),
    )
    op.create_index(
        op.f("ix_extraction_runs_document_id"), "extraction_runs", ["document_id"], unique=False
    )
    op.create_index(op.f("ix_extraction_runs_status"), "extraction_runs", ["status"], unique=False)

    # 4. candidate_skills
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("skill_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            name=op.f("fk_candidate_skills_extraction_run_id_extraction_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["users.id"],
            name=op.f("fk_candidate_skills_candidate_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_skills")),
    )
    op.create_index(
        op.f("ix_candidate_skills_extraction_run_id"),
        "candidate_skills",
        ["extraction_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_skills_candidate_id"), "candidate_skills", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_candidate_skills_skill_name"), "candidate_skills", ["skill_name"], unique=False
    )

    # 5. evidence_items
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("source_excerpt", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("grounding_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            name=op.f("fk_evidence_items_extraction_run_id_extraction_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_evidence_items_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_items")),
    )
    op.create_index(
        op.f("ix_evidence_items_extraction_run_id"),
        "evidence_items",
        ["extraction_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_document_id"), "evidence_items", ["document_id"], unique=False
    )
    op.create_index(
        "ix_evidence_items_doc_page", "evidence_items", ["document_id", "source_page"], unique=False
    )

    # 6. jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employer_id", sa.Uuid(), nullable=False),
        sa.Column("external_requisition_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employer_id"],
            ["users.id"],
            name=op.f("fk_jobs_employer_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_employer_id"), "jobs", ["employer_id"], unique=False)
    op.create_index(
        op.f("ix_jobs_external_requisition_id"), "jobs", ["external_requisition_id"], unique=False
    )
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)

    # 7. job_criteria
    op.create_table(
        "job_criteria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_job_criteria_job_id_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_criteria")),
        sa.UniqueConstraint("job_id", "name", "version", name="uq_job_criteria_job_name_version"),
    )
    op.create_index(op.f("ix_job_criteria_job_id"), "job_criteria", ["job_id"], unique=False)

    # 8. applications
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("primary_document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name=op.f("fk_applications_job_id_jobs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["users.id"],
            name=op.f("fk_applications_candidate_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["primary_document_id"],
            ["documents.id"],
            name=op.f("fk_applications_primary_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_applications_candidate_id"), "applications", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_applications_primary_document_id"),
        "applications",
        ["primary_document_id"],
        unique=False,
    )
    op.create_index(op.f("ix_applications_status"), "applications", ["status"], unique=False)

    # 9. evaluations
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("job_criteria_version", sa.Integer(), nullable=False),
        sa.Column("extraction_run_id", sa.Uuid(), nullable=False),
        sa.Column("overall_status", sa.String(length=50), nullable=False),
        sa.Column("summary_notes", sa.Text(), nullable=True),
        sa.Column("raw_model_output", sa.JSON(), nullable=False),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_evaluations_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            name=op.f("fk_evaluations_extraction_run_id_extraction_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluations")),
        sa.UniqueConstraint("application_id", "version", name="uq_evaluations_app_version"),
    )
    op.create_index(
        op.f("ix_evaluations_application_id"), "evaluations", ["application_id"], unique=False
    )
    op.create_index(
        op.f("ix_evaluations_extraction_run_id"), "evaluations", ["extraction_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_evaluations_overall_status"), "evaluations", ["overall_status"], unique=False
    )
    op.create_index(op.f("ix_evaluations_is_latest"), "evaluations", ["is_latest"], unique=False)

    # 10. criterion_evidence
    op.create_table(
        "criterion_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("job_criterion_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_item_id", sa.Uuid(), nullable=True),
        sa.Column("ai_status", sa.String(length=50), nullable=False),
        sa.Column("ai_confidence", sa.Float(), nullable=False),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("verification_state", sa.String(length=50), nullable=False),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["evaluations.id"],
            name=op.f("fk_criterion_evidence_evaluation_id_evaluations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_criterion_id"],
            ["job_criteria.id"],
            name=op.f("fk_criterion_evidence_job_criterion_id_job_criteria"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_item_id"],
            ["evidence_items.id"],
            name=op.f("fk_criterion_evidence_evidence_item_id_evidence_items"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_criterion_evidence")),
    )
    op.create_index(
        op.f("ix_criterion_evidence_evaluation_id"),
        "criterion_evidence",
        ["evaluation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_criterion_evidence_job_criterion_id"),
        "criterion_evidence",
        ["job_criterion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_criterion_evidence_evidence_item_id"),
        "criterion_evidence",
        ["evidence_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_criterion_evidence_ai_status"), "criterion_evidence", ["ai_status"], unique=False
    )
    op.create_index(
        op.f("ix_criterion_evidence_verification_state"),
        "criterion_evidence",
        ["verification_state"],
        unique=False,
    )
    op.create_index(
        "ix_criterion_evidence_eval_criterion",
        "criterion_evidence",
        ["evaluation_id", "job_criterion_id"],
        unique=False,
    )

    # 11. review_flags
    op.create_table(
        "review_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_review_flags_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_evidence_id"],
            ["criterion_evidence.id"],
            name=op.f("fk_review_flags_criterion_evidence_id_criterion_evidence"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name=op.f("fk_review_flags_assigned_to_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_flags")),
    )
    op.create_index(
        op.f("ix_review_flags_application_id"), "review_flags", ["application_id"], unique=False
    )
    op.create_index(
        op.f("ix_review_flags_criterion_evidence_id"),
        "review_flags",
        ["criterion_evidence_id"],
        unique=False,
    )
    op.create_index(op.f("ix_review_flags_status"), "review_flags", ["status"], unique=False)
    op.create_index(
        op.f("ix_review_flags_assigned_to_user_id"),
        "review_flags",
        ["assigned_to_user_id"],
        unique=False,
    )

    # 12. correction_requests
    op.create_table(
        "correction_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_statement", sa.Text(), nullable=False),
        sa.Column("additional_document_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_correction_requests_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["users.id"],
            name=op.f("fk_correction_requests_candidate_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_evidence_id"],
            ["criterion_evidence.id"],
            name=op.f("fk_correction_requests_criterion_evidence_id_criterion_evidence"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["additional_document_id"],
            ["documents.id"],
            name=op.f("fk_correction_requests_additional_document_id_documents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name=op.f("fk_correction_requests_reviewed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_correction_requests")),
    )
    op.create_index(
        op.f("ix_correction_requests_application_id"),
        "correction_requests",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correction_requests_candidate_id"),
        "correction_requests",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correction_requests_criterion_evidence_id"),
        "correction_requests",
        ["criterion_evidence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_correction_requests_status"), "correction_requests", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_correction_requests_reviewed_by_user_id"),
        "correction_requests",
        ["reviewed_by_user_id"],
        unique=False,
    )

    # 13. review_decisions
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("mandatory_rationale", sa.Text(), nullable=False),
        sa.Column("previous_verification_state", sa.String(length=64), nullable=False),
        sa.Column("new_verification_state", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(mandatory_rationale)) > 0", name="ck_review_decisions_rationale_not_empty"
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_review_decisions_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_evidence_id"],
            ["criterion_evidence.id"],
            name=op.f("fk_review_decisions_criterion_evidence_id_criterion_evidence"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_review_decisions_reviewer_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_decisions")),
    )
    op.create_index(
        op.f("ix_review_decisions_application_id"),
        "review_decisions",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_decisions_criterion_evidence_id"),
        "review_decisions",
        ["criterion_evidence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_decisions_reviewer_id"), "review_decisions", ["reviewer_id"], unique=False
    )
    op.create_index(
        op.f("ix_review_decisions_decision"), "review_decisions", ["decision"], unique=False
    )
    op.create_index(
        op.f("ix_review_decisions_is_active"), "review_decisions", ["is_active"], unique=False
    )


def downgrade() -> None:
    op.drop_table("review_decisions")
    op.drop_table("correction_requests")
    op.drop_table("review_flags")
    op.drop_table("criterion_evidence")
    op.drop_table("evaluations")
    op.drop_table("applications")
    op.drop_table("job_criteria")
    op.drop_table("jobs")
    op.drop_table("evidence_items")
    op.drop_table("candidate_skills")
    op.drop_table("extraction_runs")
    op.drop_table("documents")
    op.drop_table("users")
