"""Deprecated schema bootstrap retained as a fail-closed compatibility shim."""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def upgrade_legacy_schema(engine: Engine) -> None:
    """Refuse implicit schema edits; all upgrades must go through Alembic."""
    tables = set(inspect(engine).get_table_names())
    if tables:
        raise RuntimeError(
            "Automatic schema bootstrap is disabled for populated databases. "
            "Verify the database and apply the reviewed Alembic migrations instead."
        )
