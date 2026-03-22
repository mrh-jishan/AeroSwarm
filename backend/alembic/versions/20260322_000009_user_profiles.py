"""User profile fields

Revision ID: 20260322_000009
Revises: 20260318_000008
Create Date: 2026-03-22 00:45:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260322_000009"
down_revision = "20260318_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "bio")
    op.drop_column("users", "timezone")
    op.drop_column("users", "company_name")
    op.drop_column("users", "job_title")
    op.drop_column("users", "full_name")
