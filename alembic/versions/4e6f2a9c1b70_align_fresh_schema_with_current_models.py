"""Complete the fresh-install schema to match the current ORM.

Revision ID: 4e6f2a9c1b70
Revises: 3c8b6a1f42d9
"""
from alembic import op
import sqlalchemy as sa


revision = "4e6f2a9c1b70"
down_revision = "3c8b6a1f42d9"
branch_labels = None
depends_on = None


def _columns(inspector, table):
    return {column["name"] for column in inspector.get_columns(table)}


def _rename_if_needed(table, old_name, new_name):
    inspector = sa.inspect(op.get_bind())
    columns = _columns(inspector, table)
    if old_name not in columns:
        return
    if new_name in columns:
        # Preserve populated legacy values if both names exist from a partial
        # manual upgrade. Never overwrite a value already in the current field.
        if table == "agent_invocations":
            op.execute(sa.text(
                f'UPDATE "{table}" SET "{new_name}" = "{old_name}" '
                f'WHERE "{new_name}" IS NULL OR "{new_name}" = :empty'
            ).bindparams(empty=""))
        else:
            op.execute(sa.text(
                f'UPDATE "{table}" SET "{new_name}" = "{old_name}" '
                f'WHERE "{new_name}" IS NULL'
            ))
        return
    with op.batch_alter_table(table) as batch:
        batch.alter_column(old_name, new_column_name=new_name)


def _add_column_if_missing(table, column):
    if column.name in _columns(sa.inspect(op.get_bind()), table):
        return
    with op.batch_alter_table(table) as batch:
        batch.add_column(column)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # The original prototype migration used these names. Rename them in place
    # so their values survive and the current API/ORM sees the canonical names.
    _rename_if_needed("agents", "price_per_token", "price")
    _rename_if_needed("agent_purchases", "tokens_purchased", "purchase_price")
    _rename_if_needed("agent_invocations", "output", "output_data")

    # Fail clearly instead of silently inventing prices when neither legacy nor
    # current price columns exist.
    inspector = sa.inspect(bind)
    for table, expected in (("agents", "price"), ("agent_purchases", "purchase_price")):
        columns = _columns(inspector, table)
        if expected not in columns:
            raise RuntimeError(
                f"Cannot align {table}: expected canonical column {expected} or its recognized "
                "legacy equivalent. No source data was changed."
            )

    # Add only nullable or safely defaulted columns; all existing records remain.
    _add_column_if_missing("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("agents", sa.Column("minimum_price", sa.Float(), nullable=True))
    _add_column_if_missing("agent_invocations", sa.Column("output_data", sa.String(), nullable=True))
    if "purchase_id" not in _columns(sa.inspect(bind), "agent_invocations"):
        with op.batch_alter_table("agent_invocations") as batch:
            batch.add_column(sa.Column("purchase_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_agent_invocations_purchase_id_agent_purchases",
                "agent_purchases",
                ["purchase_id"],
                ["id"],
            )
    _add_column_if_missing("agent_invocations", sa.Column("summary", sa.String(), nullable=True))
    if "negotiation_id" not in _columns(sa.inspect(bind), "agent_invocations"):
        with op.batch_alter_table("agent_invocations") as batch:
            batch.add_column(sa.Column("negotiation_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_agent_invocations_negotiation_id_negotiations",
                "negotiations",
                ["negotiation_id"],
                ["id"],
            )
    _add_column_if_missing("agent_invocations", sa.Column("idempotency_key", sa.String(length=255), nullable=True))

    # The historic chain never created these marketplace tables on a fresh DB.
    # Create only missing tables from the current metadata; existing tables and
    # their records are never dropped or rewritten.
    if "negotiations" not in tables:
        op.create_table(
            "negotiations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False),
            sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("buyer_budget", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="open"),
            sa.Column("agreed_price", sa.Float(), nullable=True),
            sa.Column("round_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_negotiations_agent_id", "negotiations", ["agent_id"])
        op.create_index("ix_negotiations_buyer_id", "negotiations", ["buyer_id"])
        op.create_index("ix_negotiations_provider_id", "negotiations", ["provider_id"])

    if "negotiation_offers" not in tables:
        op.create_table(
            "negotiation_offers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("negotiation_id", sa.Integer(), sa.ForeignKey("negotiations.id"), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("actor_role", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_negotiation_offers_negotiation_id", "negotiation_offers", ["negotiation_id"])

    if "token_transactions" not in tables:
        op.create_table(
            "token_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("invocation_id", sa.Integer(), sa.ForeignKey("agent_invocations.id"), nullable=True),
            sa.Column("negotiation_id", sa.Integer(), sa.ForeignKey("negotiations.id"), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("idempotency_key", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("settled_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("invocation_id", name="uq_token_transaction_invocation"),
            sa.UniqueConstraint("idempotency_key", name="uq_token_transactions_idempotency_key"),
        )
        op.create_index("ix_token_transactions_user_id", "token_transactions", ["user_id"])
        op.create_index("ix_token_transactions_provider_id", "token_transactions", ["provider_id"])

    # An idempotency key must be unique. Stop before creating the index if an
    # existing database contains duplicate non-null values.
    duplicates = bind.execute(sa.text(
        "SELECT idempotency_key FROM agent_invocations "
        "WHERE idempotency_key IS NOT NULL GROUP BY idempotency_key HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError(
            "Cannot add invocation idempotency protection: duplicate idempotency_key "
            f"{duplicates[0]!r} already exists. Resolve duplicates without deleting invocation history, then retry."
        )
    index_names = {index["name"] for index in sa.inspect(bind).get_indexes("agent_invocations")}
    if "uq_agent_invocations_idempotency_key" not in index_names:
        op.create_index(
            "uq_agent_invocations_idempotency_key",
            "agent_invocations",
            ["idempotency_key"],
            unique=True,
        )


def downgrade():
    # This is a compatibility/alignment migration. Downgrading by dropping
    # columns or tables could delete live marketplace data, so retain the schema.
    pass
