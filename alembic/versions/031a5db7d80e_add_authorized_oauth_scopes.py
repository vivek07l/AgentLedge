"""Persist requested OAuth scopes on one-time authorization codes.

Revision ID: 031a5db7d80e
Revises: f17c2e80a391
"""
from alembic import op
import sqlalchemy as sa


revision = "031a5db7d80e"
down_revision = "f17c2e80a391"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "oauth_authorization_codes",
        sa.Column("scopes", sa.String(), nullable=False, server_default="marketplace:read"),
    )
    # SQLite cannot ALTER COLUMN DROP DEFAULT directly; batch mode recreates
    # the table there while remaining a normal ALTER on PostgreSQL.
    with op.batch_alter_table("oauth_authorization_codes") as batch_op:
        batch_op.alter_column("scopes", server_default=None)


def downgrade() -> None:
    op.drop_column("oauth_authorization_codes", "scopes")
