"""add tokens_remaining to agent_purchases

Revision ID: 418451761ac7
Revises: 017a5cc7a6d2
Create Date: 2025-02-14 21:59:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '418451761ac7'
down_revision: Union[str, None] = '017a5cc7a6d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some legacy databases may already have received this additive column
    # before Alembic tracking was introduced. Keep the historical revision
    # safe to resume without attempting to add the same column twice.
    inspector = sa.inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("agent_purchases")}
    if "tokens_remaining" in existing_columns:
        return

    with op.batch_alter_table('agent_purchases') as batch_op:
        batch_op.add_column(sa.Column('tokens_remaining', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    # Remove tokens_remaining column from agent_purchases table
    with op.batch_alter_table('agent_purchases') as batch_op:
        batch_op.drop_column('tokens_remaining')
