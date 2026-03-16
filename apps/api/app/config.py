import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # =========================
    # App
    # =========================
    APP_NAME: str = "Vikki"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # =========================
    # JWT
    # =========================
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ALGORITHM: str = "HS256"

    # =========================
    # Database
    # =========================
    DATABASE_URL: str | None = None

    POSTGRES_USER: str = "vikki"
    POSTGRES_PASSWORD: str = "vikki"
    POSTGRES_DB: str = "vikki_dev"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    @property
    def database_url(self) -> str:
        """
        Async URL для web/app слоя.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL.strip()
            if url.startswith("postgresql+asyncpg://"):
                return url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_sync_url(self) -> str:
        """
        Sync URL для Celery/Alembic/sync задач.
        КРИТИЧНО: никогда не возвращать asyncpg URL.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL.strip()
            if url.startswith("postgresql+asyncpg://"):
                return url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url

        env_sync = os.getenv("DATABASE_URL_SYNC")
        if env_sync:
            env_sync = env_sync.strip()
            if env_sync.startswith("postgresql+asyncpg://"):
                return env_sync.replace("postgresql+asyncpg://", "postgresql://", 1)
            return env_sync

        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # =========================
    # Redis
    # =========================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # =========================
    # Celery
    # =========================
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # =========================
    # MinIO
    # =========================
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vikki"

    # =========================
    # IMAP (Email ingest)
    # =========================
    IMAP_ENABLED: bool = False

    IMAP_HOST: str | None = None
    IMAP_PORT: int = 993
    IMAP_SSL: bool = True

    IMAP_USERNAME: str | None = None
    IMAP_PASSWORD: str | None = None

    IMAP_MAILBOX: str = "INBOX"

    IMAP_SUBJECT_CONTAINS: str | None = None
    IMAP_FROM_CONTAINS: str | None = None
    IMAP_ALLOWED_EXTENSIONS: str | None = None

    IMAP_MAX_MESSAGES_PER_RUN: int = 25
    IMAP_MAX_ATTACHMENTS_PER_MESSAGE: int = 10
    IMAP_MAX_ATTACHMENT_BYTES: int = 25_000_000
    IMAP_TIMEOUT_SECONDS: int = 30

    IMAP_POLL_INTERVAL_MINUTES: int = 5
    IMAP_TENANT_SLUG: str | None = None
    IMAP_DEFAULT_BANK_ACCOUNT_ID: str | None = None

    IMAP_SEARCH_MODE: str = "ALL_LAST_N"
    IMAP_LAST_N: int = 50
    IMAP_SEARCH_SINCE_DAYS: int = 7
    IMAP_MARK_SEEN_ONLY_ON_SUCCESS: bool = True

    # =========================
    # Sber download / TLS
    # =========================
    SBER_TLS_VERIFY: bool = True
    SBER_CA_CERT_PATH: str | None = None
    SBER_DOWNLOAD_TIMEOUT_SECONDS: int = 30
    SBER_DOWNLOAD_RETRIES: int = 3
    SBER_DOWNLOAD_RETRY_DELAY_SECONDS: int = 5

    class Config:
        env_file = ".env"


settings = Settings()