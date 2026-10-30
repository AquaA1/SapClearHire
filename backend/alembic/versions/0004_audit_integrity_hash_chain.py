"""Add hash chain and state columns to audit_events

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "audit_events",
        sa.Column("entity_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("prior_state", sa.JSON(), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("new_state", sa.JSON(), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("event_hash", sa.String(length=64), nullable=False, server_default="0" * 64),
    )

    op.create_index(
        op.f("ix_audit_events_sequence_number"),
        "audit_events",
        ["sequence_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_audit_events_previous_hash"),
        "audit_events",
        ["previous_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_event_hash"),
        "audit_events",
        ["event_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_event_hash"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_previous_hash"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_sequence_number"), table_name="audit_events")
    op.drop_column("audit_events", "event_hash")
    op.drop_column("audit_events", "previous_hash")
    op.drop_column("audit_events", "new_state")
    op.drop_column("audit_events", "prior_state")
    op.drop_column("audit_events", "entity_version")
    op.drop_column("audit_events", "sequence_number")
