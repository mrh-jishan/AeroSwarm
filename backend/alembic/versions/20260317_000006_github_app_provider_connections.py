"""GitHub App provider connections

Revision ID: 20260317_000006
Revises: 20260317_000005
Create Date: 2026-03-17 19:10:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260317_000006"
down_revision = "20260317_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_connections",
        sa.Column("auth_mode", sa.String(length=20), nullable=False, server_default="token"),
    )
    op.add_column(
        "provider_connections",
        sa.Column("installation_id", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "provider_connections",
        "encrypted_access_token",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "provider_connections",
        "auth_mode",
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "provider_connections",
        "encrypted_access_token",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("provider_connections", "installation_id")
    op.drop_column("provider_connections", "auth_mode")
