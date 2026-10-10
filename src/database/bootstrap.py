"""Small, additive compatibility upgrades for older local prototype databases.

The repository's historic Alembic chain is inconsistent. This bootstrap only
adds the admin flag that recent API code requires; it never drops or rewrites
user data. Proper versioned migrations remain the deployment path.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade_legacy_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not tables:
        return  # create_all will create the current schema on a fresh database.

    boolean_false = "0" if engine.dialect.name == "sqlite" else "FALSE"
    additions = {
        "users": {"is_admin": f"BOOLEAN NOT NULL DEFAULT {boolean_false}"},
        "agents": {"minimum_price": "FLOAT"},
        "agent_invocations": {
            "negotiation_id": "INTEGER",
            "idempotency_key": "VARCHAR(255)",
        },
        "token_transactions": {"provider_id": "INTEGER"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for column, definition in columns.items():
                if column not in existing:
                    connection.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    ))
        if "agent_invocations" in tables:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_invocations_idempotency_key "
                "ON agent_invocations (idempotency_key)"
            ))
