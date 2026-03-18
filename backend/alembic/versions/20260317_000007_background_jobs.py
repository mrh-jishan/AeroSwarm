"""background jobs and async state columns

Revision ID: 20260317_000007
Revises: 20260317_000006
Create Date: 2026-03-17 21:45:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260317_000007"
down_revision = "20260317_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("merge_requests", sa.Column("checks_json", sa.Text(), nullable=True))
    op.add_column("merge_requests", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("merge_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["merge_request_id"], ["merge_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_background_jobs_status_available_at", "background_jobs", ["status", "available_at"])
    op.alter_column("background_jobs", "attempts", server_default=None)
    op.alter_column("background_jobs", "max_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_background_jobs_status_available_at", table_name="background_jobs")
    op.drop_table("background_jobs")
    op.drop_column("merge_requests", "error_message")
    op.drop_column("merge_requests", "checks_json")
    op.drop_column("sessions", "error_message")
