"""Add per-user OAuth clients, PKCE codes, and scoped access tokens.

Revision ID: f17c2e80a391
Revises: a41f8296d310
"""
from alembic import op
import sqlalchemy as sa

revision = "f17c2e80a391"
down_revision = "a41f8296d310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("client_id", sa.String(), primary_key=True),
        sa.Column("redirect_uris_json", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "oauth_authorization_codes",
        sa.Column("code_hash", sa.String(), primary_key=True),
        sa.Column("client_id", sa.String(), sa.ForeignKey("oauth_clients.client_id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redirect_uri", sa.String(), nullable=False),
        sa.Column("code_challenge", sa.String(), nullable=False),
        sa.Column("code_challenge_method", sa.String(), nullable=False),
        sa.Column("audience", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_oauth_authorization_codes_client_id", "oauth_authorization_codes", ["client_id"])
    op.create_index("ix_oauth_authorization_codes_user_id", "oauth_authorization_codes", ["user_id"])
    op.create_table(
        "oauth_access_tokens",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column("client_id", sa.String(), sa.ForeignKey("oauth_clients.client_id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scopes", sa.String(), nullable=False),
        sa.Column("audience", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_oauth_access_tokens_client_id", "oauth_access_tokens", ["client_id"])
    op.create_index("ix_oauth_access_tokens_user_id", "oauth_access_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_oauth_access_tokens_user_id", table_name="oauth_access_tokens")
    op.drop_index("ix_oauth_access_tokens_client_id", table_name="oauth_access_tokens")
    op.drop_table("oauth_access_tokens")
    op.drop_index("ix_oauth_authorization_codes_user_id", table_name="oauth_authorization_codes")
    op.drop_index("ix_oauth_authorization_codes_client_id", table_name="oauth_authorization_codes")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")
