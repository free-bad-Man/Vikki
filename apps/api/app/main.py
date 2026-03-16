import os
import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.test import router as test_router
from app.routers.bank_accounts import router as bank_accounts_router
from app.routers.bank_import import router as bank_import_router
from app.routers.transactions import router as transactions_router
from app.routers.edo_documents import router as edo_documents_router
from app.routers.cash_operations import router as cash_operations_router
from app.routers.sbis_webhook import router as sbis_webhook_router
from app.routers.notifications import router as notifications_router
from app.routers.analytics import router as analytics_router
from app.routers.bank_analytics import router as bank_analytics_router

app = FastAPI(title="Vikki API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(test_router)
app.include_router(bank_accounts_router)
app.include_router(bank_import_router)
app.include_router(transactions_router)
app.include_router(edo_documents_router)
app.include_router(cash_operations_router)
app.include_router(sbis_webhook_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(bank_analytics_router)


@app.on_event("startup")
async def startup_event():
    """
    Опциональный запуск миграций Alembic на старте.
    Только для dev-окружения при флаге RUN_MIGRATIONS_ON_STARTUP=true.
    """
    if os.getenv("RUN_MIGRATIONS_ON_STARTUP", "false").lower() == "true":
        try:
            subprocess.run(
                ["alembic", "upgrade", "head"],
                check=True,
                capture_output=True,
                text=True,
            )
            print("Alembic migrations applied successfully")
        except subprocess.CalledProcessError as e:
            print(f"Failed to apply migrations: {e.stderr}")
            raise


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api"}


@app.get("/")
async def root():
    return {"message": "Vikki API is running", "docs": "/docs"}