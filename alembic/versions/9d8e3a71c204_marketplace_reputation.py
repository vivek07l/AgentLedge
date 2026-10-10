"""Add marketplace discovery fields and verified reviews."""
from alembic import op
import sqlalchemy as sa

revision = "9d8e3a71c204"
down_revision = "418451761ac7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(), nullable=False, server_default="General"))
        batch_op.add_column(sa.Column("capabilities", sa.String(), nullable=False, server_default=""))
    op.create_table(
        "agent_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("invocation_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.String(), nullable=True),
        sa.Column("moderation_status", sa.String(), nullable=False, server_default="approved"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invocation_id"], ["agent_invocations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invocation_id", name="uq_agent_review_invocation"),
    )
    op.create_index("ix_agent_reviews_agent_id", "agent_reviews", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_reviews_agent_id", table_name="agent_reviews")
    op.drop_table("agent_reviews")
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_column("capabilities")
        batch_op.drop_column("category")
