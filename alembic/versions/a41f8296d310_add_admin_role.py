"""Add explicit admin role to users."""
from alembic import op
import sqlalchemy as sa

revision = "a41f8296d310"
down_revision = "9d8e3a71c204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_admin")
