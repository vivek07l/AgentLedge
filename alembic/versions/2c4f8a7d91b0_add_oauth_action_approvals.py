"""Add pending, one-time approval records for AgentMesh write actions.

Revision ID: 2c4f8a7d91b0
Revises: 031a5db7d80e
"""
from alembic import op
import sqlalchemy as sa


revision = "2c4f8a7d91b0"
down_revision = "031a5db7d80e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_action_approvals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_oauth_action_approvals_user_id", "oauth_action_approvals", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_action_approvals_user_id", table_name="oauth_action_approvals")
    op.drop_table("oauth_action_approvals")
