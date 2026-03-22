"""Session LLM provider and model selection

Revision ID: 20260318_000008
Revises: 20260317_000007
Create Date: 2026-03-18 00:30:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260318_000008"
down_revision = "20260317_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("llm_provider", sa.String(length=20), nullable=False, server_default="gemini"),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "manager_model",
            sa.String(length=100),
            nullable=False,
            server_default="gemini-2.5-flash",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "agent_model",
            sa.String(length=100),
            nullable=False,
            server_default="gemini-2.5-flash",
        ),
    )
    op.alter_column("sessions", "llm_provider", server_default=None)
    op.alter_column("sessions", "manager_model", server_default=None)
    op.alter_column("sessions", "agent_model", server_default=None)


def downgrade() -> None:
    op.drop_column("sessions", "agent_model")
    op.drop_column("sessions", "manager_model")
    op.drop_column("sessions", "llm_provider")
