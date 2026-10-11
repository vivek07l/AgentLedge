"""add tokens_remaining to agent purchase

Revision ID: 017a5cc7a6d2
Revises: bbb58327aef6
Create Date: 2025-02-14 21:38:36.404468

"""
# revision identifiers, used by Alembic.
revision = '017a5cc7a6d2'
down_revision = 'bbb58327aef6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This legacy revision accidentally duplicated the initial migration's
    # create_table operations. Revision 418451761ac7 applies the intended
    # tokens_remaining change, so this revision must remain a no-op.
    pass


def downgrade() -> None:
    pass
