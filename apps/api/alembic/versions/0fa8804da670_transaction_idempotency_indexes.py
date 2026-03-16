"""transaction idempotency indexes

Revision ID: 0fa8804da670
Revises: c4dd3f4dfa15
Create Date: 2026-02-27

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0fa8804da670"
down_revision = "c4dd3f4dfa15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Если старый unique индекс существовал — убираем (безопасно)
    try:
        op.drop_index("ix_transactions_tenant_fingerprint", table_name="transactions")
    except Exception:
        pass

    # Нужен для digest()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # Idempotency #1: внешний ID транзакции (если есть) уникален в рамках tenant+account
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_tenant_account_external_id
        ON transactions (tenant_id, bank_account_id, external_id)
        WHERE external_id IS NOT NULL
        """
    )

    # Idempotency #2: fingerprint (fallback) уникален в рамках tenant
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_tenant_fingerprint
        ON transactions (tenant_id, fingerprint)
        WHERE fingerprint IS NOT NULL
        """
    )

    # Backfill fingerprint для существующих строк (только где NULL)
    op.execute(
        """
        UPDATE transactions
        SET fingerprint = encode(
            digest(
                coalesce(tenant_id::text,'') || '|' ||
                coalesce(bank_account_id::text,'') || '|' ||
                coalesce(occurred_at::text,'') || '|' ||
                coalesce(amount::text,'') || '|' ||
                coalesce(transaction_type,'') || '|' ||
                coalesce(counterparty_inn,'') || '|' ||
                coalesce(description,'') || '|' ||
                coalesce(document_number,'')
            , 'sha256')
        , 'hex')
        WHERE fingerprint IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_transactions_tenant_account_external_id")
    op.execute("DROP INDEX IF EXISTS ux_transactions_tenant_fingerprint")

    op.create_index(
        "ix_transactions_tenant_fingerprint",
        "transactions",
        ["tenant_id", "fingerprint"],
        unique=True,
    )