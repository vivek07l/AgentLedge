"""Add per-listing execution configuration.

Revision ID: 72dc3f911a2e
Revises: 3c8b6a1f42d9, 4e6f2a9c1b70
"""
from alembic import op
import sqlalchemy as sa


revision = "72dc3f911a2e"
down_revision = ("3c8b6a1f42d9", "4e6f2a9c1b70")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("execution_instructions", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("expected_input", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("input_schema_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("output_format", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_column("output_format")
        batch_op.drop_column("input_schema_json")
        batch_op.drop_column("expected_input")
        batch_op.drop_column("execution_instructions")
