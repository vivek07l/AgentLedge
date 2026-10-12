"""Add opt-in account-level autonomous execution limits.

Revision ID: 8a72d421c550
Revises: 72dc3f911a2e
"""
from alembic import op
import sqlalchemy as sa


revision = "8a72d421c550"
down_revision = "72dc3f911a2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "autonomous_execution_policies",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("max_task_budget", sa.Float(), nullable=False, server_default="5"),
        sa.Column("max_offer_price", sa.Float(), nullable=False, server_default="5"),
        sa.Column("max_daily_spend", sa.Float(), nullable=False, server_default="10"),
        sa.Column("allowed_categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("allowed_listing_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("max_negotiation_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_execution_retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("autonomous_execution_policies")
