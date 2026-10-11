from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from alembic import context

from src.database.models import Base
from src.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Databases created before Alembic was introduced need a carefully verified
# adoption point. This is the last revision whose tables are all expected in
# the deployed legacy schema; the following revisions are additive and safe
# to apply there. In particular, we do not stamp the full head because the
# legacy database is missing these later additions.
LEGACY_BASELINE = "f17c2e80a391"
LEGACY_REQUIRED_TABLES = {
    "users",
    "agents",
    "agent_purchases",
    "agent_invocations",
    "agent_reviews",
    "negotiations",
    "negotiation_offers",
    "token_transactions",
    "oauth_clients",
    "oauth_authorization_codes",
    "oauth_access_tokens",
}


class UnsafeLegacySchema(RuntimeError):
    """Raised when an unversioned database cannot be safely adopted."""


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _adopt_verified_legacy_database(connection) -> None:
    """Record the verified baseline before Alembic executes additive revisions.

    This deliberately rejects partial, unexpected, or partially migrated
    schemas. It does not alter application tables or data.
    """
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    allow_adoption = context.get_x_argument(as_dictionary=True).get("adopt_legacy") == "true"
    if "alembic_version" in tables:
        versions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if versions:
            if len(versions) != 1:
                raise UnsafeLegacySchema(
                    "The database has multiple Alembic revisions recorded, but this project expects one linear head. "
                    "Inspect and reconcile its migration history before upgrading."
                )
            connection.commit()
            return
        if not (tables - {"alembic_version"}):
            connection.commit()
            return
        raise UnsafeLegacySchema(
            "The database has an empty alembic_version table alongside application tables. "
            "Inspect its migration history and reconcile it manually; automatic baseline adoption is unsafe."
        )

    # A genuinely empty database follows the complete fresh-install chain.
    app_tables = tables - {"alembic_version"}
    if not app_tables:
        # Inspector calls can autobegin a SQLAlchemy transaction even on an
        # empty SQLite database; close it before Alembic starts its migration
        # transaction or SQLite may roll back the version marker on exit.
        connection.commit()
        return

    if not allow_adoption:
        raise UnsafeLegacySchema(
            "This database has application tables but no Alembic history. It was not changed. "
            "After verifying a backup and confirming the schema matches the documented legacy shape, "
            "run `alembic -x adopt_legacy=true upgrade head`."
        )

    missing_tables = sorted(LEGACY_REQUIRED_TABLES - tables)
    if missing_tables:
        raise UnsafeLegacySchema(
            "Refusing to run Alembic on an unversioned, unrecognized database. "
            "Missing expected legacy tables: " + ", ".join(missing_tables) +
            ". Verify the database schema and create a reviewed baseline before retrying."
        )

    required_columns = {
        "users": {"id", "username", "email", "hashed_password", "is_developer", "token_balance", "created_at", "is_active"},
        "agents": {"id", "name", "description", "developer_id", "is_active", "created_at", "category", "capabilities"},
        "agent_purchases": {"id", "user_id", "agent_id", "purchase_date"},
        "agent_invocations": {"id", "user_id", "agent_id", "input_data", "tokens_used", "status", "created_at"},
        "agent_reviews": {"id", "agent_id", "reviewer_user_id", "invocation_id", "rating", "moderation_status", "created_at"},
        "negotiations": {"id", "agent_id", "buyer_id", "provider_id", "buyer_budget", "status", "created_at"},
        "negotiation_offers": {"id", "negotiation_id", "actor_role", "action", "created_at"},
        "token_transactions": {"id", "user_id", "amount", "status", "created_at"},
        "oauth_clients": {"client_id", "redirect_uris_json", "created_at"},
        "oauth_authorization_codes": {"code_hash", "client_id", "user_id", "redirect_uri", "code_challenge", "code_challenge_method", "audience", "expires_at", "created_at"},
        "oauth_access_tokens": {"token_hash", "client_id", "user_id", "scopes", "audience", "expires_at", "revoked_at", "created_at"},
    }
    mismatches = []
    for table, expected in required_columns.items():
        absent = sorted(expected - _columns(inspector, table))
        if absent:
            mismatches.append(f"{table} missing columns [{', '.join(absent)}]")

    # These additions prove the target is the known post-baseline schema and
    # avoid treating a partially migrated database as a valid legacy baseline.
    # tokens_remaining is intentionally optional: the known production schema
    # lacks it, and adoption adds it with a safe zero default below.
    if not ({"price", "price_per_token"} & _columns(inspector, "agents")):
        mismatches.append("agents has neither price nor legacy price_per_token")
    if not ({"purchase_price", "tokens_purchased"} & _columns(inspector, "agent_purchases")):
        mismatches.append("agent_purchases has neither purchase_price nor legacy tokens_purchased")
    if "implementation_key" in _columns(inspector, "agents"):
        mismatches.append("agents.implementation_key already exists")
    # The application schema represented by the baseline must include the
    # deployed OAuth tables and the discovery/reputation tables; the later
    # migrations intentionally add only the listed missing fields/tables.
    if "scopes" in _columns(inspector, "oauth_authorization_codes"):
        mismatches.append("oauth_authorization_codes.scopes already exists")
    if "oauth_action_approvals" in tables:
        mismatches.append("oauth_action_approvals already exists")

    if mismatches:
        raise UnsafeLegacySchema(
            "Refusing to adopt an unversioned database because its schema does not "
            "match the verified legacy baseline: " + "; ".join(mismatches) +
            ". Inspect its migration state and reconcile it manually before retrying."
        )

    try:
        purchase_columns = _columns(inspector, "agent_purchases")
        if "tokens_remaining" not in purchase_columns:
            # Adding a non-null zero default preserves every purchase record
            # and makes existing rows compatible with the current ORM.
            connection.execute(text(
                "ALTER TABLE agent_purchases ADD COLUMN tokens_remaining FLOAT NOT NULL DEFAULT 0.0"
            ))
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": LEGACY_BASELINE},
        )
        # Commit the verified marker before invoking Alembic's migration
        # transaction. If a later additive revision fails, the database stays
        # at the verified baseline and can safely resume on the next attempt.
        connection.commit()
    except SQLAlchemyError as exc:
        raise UnsafeLegacySchema(
            "Could not record the verified Alembic baseline. No application tables "
            "were changed; inspect alembic_version and retry after resolving the database error."
        ) from exc

# Set the SQLAlchemy URL from our settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _adopt_verified_legacy_database(connection)
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
