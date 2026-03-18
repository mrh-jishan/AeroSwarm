"""Provider connections and GitHub PR fields

Revision ID: 20260317_000005
Revises: 20260317_000004
Create Date: 2026-03-17 18:25:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260317_000005"
down_revision = "20260317_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_connections_user_provider_account",
        "provider_connections",
        ["user_id", "provider", "account_login"],
        unique=True,
    )

    op.add_column(
        "sessions",
        sa.Column("provider_connection_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("sessions", sa.Column("vcs_provider", sa.String(length=20), nullable=True))
    op.add_column("sessions", sa.Column("repo_owner", sa.String(length=255), nullable=True))
    op.add_column("sessions", sa.Column("repo_name", sa.String(length=255), nullable=True))
    op.add_column("sessions", sa.Column("base_branch", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_sessions_provider_connection_id",
        "sessions",
        "provider_connections",
        ["provider_connection_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("merge_requests", sa.Column("provider_pr_number", sa.Integer(), nullable=True))
    op.add_column("merge_requests", sa.Column("provider_pr_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("merge_requests", "provider_pr_url")
    op.drop_column("merge_requests", "provider_pr_number")

    op.drop_constraint("fk_sessions_provider_connection_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "base_branch")
    op.drop_column("sessions", "repo_name")
    op.drop_column("sessions", "repo_owner")
    op.drop_column("sessions", "vcs_provider")
    op.drop_column("sessions", "provider_connection_id")

    op.drop_index(
        "ix_provider_connections_user_provider_account",
        table_name="provider_connections",
    )
    op.drop_table("provider_connections")
