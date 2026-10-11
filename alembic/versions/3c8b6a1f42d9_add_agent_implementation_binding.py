"""Bind marketplace listings to explicit supported implementations.

Revision ID: 3c8b6a1f42d9
Revises: 2c4f8a7d91b0
"""
from alembic import op
import sqlalchemy as sa


revision = "3c8b6a1f42d9"
down_revision = "2c4f8a7d91b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("implementation_key", sa.String(), nullable=True))

    # Preserve only the five canonical seeded listings as executable. Other
    # published records remain discoverable and require an explicit supported
    # implementation selection before they can run.
    builtins = (
        ("Interview Prep Assistant", "interview questions, behavioral prep, technical questions, mock feedback", "interview_prep"),
        ("Code Reviewer", "code analysis, bug detection, security checks, style suggestions, refactoring", "code_reviewer"),
        ("Resume Reviewer", "resume analysis, ATS formatting, bullet improvements, cover letters", "resume_reviewer"),
        ("Technical Troubleshooter", "root cause diagnosis, log analysis, system debugging, stack trace resolution", "technical_troubleshooter"),
        ("Writing Assistant", "copywriting, tone adjustment, proofreading, grammar, style improvement", "writing_assistant"),
    )
    for name, capabilities, implementation_key in builtins:
        op.execute(sa.text(
            "UPDATE agents SET implementation_key = :key "
            "WHERE name = :name AND capabilities = :capabilities"
        ).bindparams(key=implementation_key, name=name, capabilities=capabilities))


def downgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_column("implementation_key")
