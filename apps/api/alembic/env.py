from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import settings
from app.database import Base

# Импорт моделей для регистрации metadata в Alembic
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_database_url() -> str:
    """
    Alembic должен всегда ходить только через sync URL.
    Приоритет:
    1) settings.database_sync_url
    2) sqlalchemy.url из alembic.ini как fallback
    """
    url = settings.database_sync_url
    if url:
        return url

    fallback = config.get_main_option("sqlalchemy.url")
    if not fallback:
        raise RuntimeError("Database URL for Alembic is not configured")

    return fallback


def run_migrations_offline() -> None:
    url = _get_sync_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _get_sync_database_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()