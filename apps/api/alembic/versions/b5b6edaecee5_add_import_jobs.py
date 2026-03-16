"""add import_jobs

Revision ID: b5b6edaecee5
Revises: 0fa8804da670
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b5b6edaecee5"
down_revision = "0fa8804da670"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        # PK как varchar (в проекте tenants/users id = varchar)
        sa.Column("id", sa.String(), primary_key=True, nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),

        sa.Column("source", sa.String(length=32), nullable=False, server_default="bank"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_mime", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),

        sa.Column("s3_bucket", sa.String(length=128), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),

        sa.Column("file_sha256", sa.String(length=64), nullable=False),

        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),

        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_index("ix_import_jobs_tenant_id", "import_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"], unique=False)
    op.create_index("ix_import_jobs_deleted_at", "import_jobs", ["deleted_at"], unique=False)

    op.create_index(
        "ix_import_jobs_tenant_status_created",
        "import_jobs",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )

    op.create_index(
        "ux_import_jobs_tenant_file_sha256",
        "import_jobs",
        ["tenant_id", "file_sha256"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_import_jobs_tenant_file_sha256", table_name="import_jobs")
    op.drop_index("ix_import_jobs_tenant_status_created", table_name="import_jobs")
    op.drop_index("ix_import_jobs_deleted_at", table_name="import_jobs")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_index("ix_import_jobs_tenant_id", table_name="import_jobs")
    op.drop_table("import_jobs")