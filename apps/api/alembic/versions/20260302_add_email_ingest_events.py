"""add email_ingest_events

Revision ID: 20260302_add_email_ingest_events
Revises: b5b6edaecee5
Create Date: 2026-03-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260302_add_email_ingest_events"
down_revision = "b5b6edaecee5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_ingest_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("mailbox", sa.String(length=255), nullable=False),
        sa.Column("message_uid", sa.String(length=255), nullable=False),

        sa.Column("attachment_sha256", sa.String(length=64), nullable=False),
        sa.Column("attachment_name", sa.String(length=512), nullable=True),
        sa.Column("attachment_mime", sa.String(length=255), nullable=True),
        sa.Column("attachment_size", sa.String(length=32), nullable=True),

        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=True),

        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_email_ingest_tenant_status_created",
        "email_ingest_events",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )

    op.create_unique_constraint(
        "ux_email_ingest_tenant_mailbox_uid_sha",
        "email_ingest_events",
        ["tenant_id", "mailbox", "message_uid", "attachment_sha256"],
    )


def downgrade() -> None:
    op.drop_constraint("ux_email_ingest_tenant_mailbox_uid_sha", "email_ingest_events", type_="unique")
    op.drop_index("ix_email_ingest_tenant_status_created", table_name="email_ingest_events")
    op.drop_table("email_ingest_events")
