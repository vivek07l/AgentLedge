import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, text

from src.database.models import Base


ROOT = Path(__file__).resolve().parents[1]


def _migration_env(db_path: Path):
    env = os.environ.copy()
    env["SECRET_KEY"] = "migration-test-secret"
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    env["PYTHONPATH"] = str(ROOT)
    return env


def _alembic(db_path: Path, *args: str):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=_migration_env(db_path),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_fresh_database_reaches_model_compatible_head(tmp_path):
    db_path = tmp_path / "fresh.sqlite3"
    result = _alembic(db_path, "upgrade", "head")

    assert result.returncode == 0, result.stdout + result.stderr
    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    assert "4e6f2a9c1b70" in result.stderr
    assert {"negotiations", "negotiation_offers", "token_transactions"} <= set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        assert table_name in inspector.get_table_names()
        assert set(table.columns.keys()) <= {column["name"] for column in inspector.get_columns(table_name)}
    assert "price" in {column["name"] for column in inspector.get_columns("agents")}
    assert "purchase_price" in {column["name"] for column in inspector.get_columns("agent_purchases")}
    assert "tokens_remaining" in {column["name"] for column in inspector.get_columns("agent_purchases")}
    assert "output_data" in {column["name"] for column in inspector.get_columns("agent_invocations")}


def test_verified_unversioned_database_adopts_and_preserves_purchases(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id, username, email, hashed_password, is_developer, is_admin, token_balance, created_at, is_active) "
            "VALUES (1, 'buyer', 'buyer@example.test', 'hash', 0, 0, 45, CURRENT_TIMESTAMP, 1)"
        ))
        connection.execute(text(
            "INSERT INTO agents (id, name, description, category, capabilities, developer_id, price, minimum_price, is_active, created_at) "
            "VALUES (1, 'Service', 'Description', 'General', '', 1, 3, 1, 1, CURRENT_TIMESTAMP)"
        ))
        connection.execute(text(
            "INSERT INTO agent_purchases (id, user_id, agent_id, purchase_price, purchase_date) "
            "VALUES (7, 1, 1, 12.5, CURRENT_TIMESTAMP)"
        ))
        connection.execute(text("ALTER TABLE oauth_authorization_codes DROP COLUMN scopes"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN implementation_key"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN execution_instructions"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN expected_input"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN input_schema_json"))
        connection.execute(text("ALTER TABLE agents DROP COLUMN output_format"))
        connection.execute(text("DROP TABLE oauth_action_approvals"))
        connection.execute(text("ALTER TABLE agent_purchases DROP COLUMN tokens_remaining"))
    engine.dispose()

    refused = _alembic(db_path, "upgrade", "head")
    assert refused.returncode != 0
    assert "alembic -x adopt_legacy=true upgrade head" in refused.stderr
    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    assert "alembic_version" not in inspector.get_table_names()

    adopted = _alembic(db_path, "-x", "adopt_legacy=true", "upgrade", "head")
    assert adopted.returncode == 0, adopted.stdout + adopted.stderr
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    assert "4e6f2a9c1b70" in adopted.stderr
    with engine.connect() as connection:
        # The adopted baseline is downstream of migration 418451761ac7, so
        # its missing purchase column must be added before the baseline stamp.
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "72dc3f911a2e"
    assert {"oauth_action_approvals", "negotiations", "negotiation_offers", "token_transactions"} <= set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        assert table_name in inspector.get_table_names()
        assert set(table.columns.keys()) <= {column["name"] for column in inspector.get_columns(table_name)}
    with engine.connect() as connection:
        purchase = connection.execute(text(
            "SELECT id, purchase_price, tokens_remaining FROM agent_purchases WHERE id = 7"
        )).one()
        assert purchase == (7, 12.5, 0.0)
        assert connection.execute(text("SELECT token_balance FROM users WHERE id = 1")).scalar_one() == 45
    engine.dispose()


def test_existing_tokens_remaining_column_is_not_added_twice(tmp_path):
    db_path = tmp_path / "partially_migrated.sqlite3"
    initial = _alembic(db_path, "upgrade", "017a5cc7a6d2")
    assert initial.returncode == 0, initial.stdout + initial.stderr

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE agent_purchases ADD COLUMN tokens_remaining FLOAT NOT NULL DEFAULT 0.0"
        ))
        connection.execute(text(
            "INSERT INTO users (id, token_balance) VALUES (1, 20)"
        ))
        connection.execute(text(
            "INSERT INTO agents (id, name, price_per_token) VALUES (1, 'Service', 2)"
        ))
        connection.execute(text(
            "INSERT INTO agent_purchases (id, user_id, agent_id, tokens_purchased, purchase_date, tokens_remaining) "
            "VALUES (11, 1, 1, 8, CURRENT_TIMESTAMP, 6)"
        ))
    engine.dispose()

    upgraded = _alembic(db_path, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = inspect(engine)
    assert "tokens_remaining" in {
        column["name"] for column in inspector.get_columns("agent_purchases")
    }
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT purchase_price, tokens_remaining FROM agent_purchases WHERE id = 11"
        )).one() == (8.0, 6.0)
    engine.dispose()


def test_unrecognized_unversioned_database_fails_without_changes(tmp_path):
    db_path = tmp_path / "unknown.sqlite3"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users (id) VALUES (99)"))
    engine.dispose()

    result = _alembic(db_path, "-x", "adopt_legacy=true", "upgrade", "head")
    assert result.returncode != 0
    assert "unrecognized" in result.stderr
    inspector = inspect(create_engine(f"sqlite:///{db_path.as_posix()}"))
    assert set(inspector.get_table_names()) == {"users"}
