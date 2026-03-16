"""add import_job_id to transactions

Revision ID: 20260309_add_import_job_id
Revises: 20260302_add_email_ingest_events
Create Date: 2026-03-09 13:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260309_add_import_job_id"
down_revision = "20260302_add_email_ingest_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("import_job_id", sa.String(), nullable=True),
        schema="public",
    )

    op.create_index(
        "ix_transactions_import_job_id",
        "transactions",
        ["import_job_id"],
        unique=False,
        schema="public",
    )

    op.create_foreign_key(
        "transactions_import_job_id_fkey",
        "transactions",
        "import_jobs",
        ["import_job_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "transactions_import_job_id_fkey",
        "transactions",
        schema="public",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_transactions_import_job_id",
        table_name="transactions",
        schema="public",
    )

    op.drop_column("transactions", "import_job_id", schema="public")
