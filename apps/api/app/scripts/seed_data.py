"""
Скрипт для создания тестовых данных.

Запуск:
    docker compose -f infra/compose/docker-compose.dev.yml run --rm api python -m app.scripts.seed_data
"""
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.models.membership import Membership
from app.utils.password import hash_password


def seed_data():
    """Создаёт тестовые данные."""
    
    # Создаём sync engine
    engine = create_engine(settings.database_sync_url, echo=False)
    session_maker = Session(engine)
    
    with session_maker as db:
        # Проверяем что таблицы существуют
        result = db.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tenants')")
        )
        if not result.scalar():
            print("❌ Таблицы не найдены. Сначала примените миграции: alembic upgrade head")
            return
        
        # Проверяем существует ли уже тестовый tenant
        result = db.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": "test-company"}
        )
        existing = result.scalar()
        
        if existing:
            print(f"⚠️  Тестовый tenant уже существует (id={existing})")
            print("   Удалите его вручную если хотите пересоздать")
            return
        
        # Создаём tenant
        tenant = Tenant(
            name="Test Company",
            slug="test-company",
        )
        db.add(tenant)
        db.flush()
        print(f"✅ Tenant создан: {tenant.id} (test-company)")
        
        # Создаём роль "admin"
        admin_role = Role(
            tenant_id=tenant.id,
            name="Admin",
            code="admin",
            description="Администратор tenant",
            permissions=["*"],
            is_system=True,
        )
        db.add(admin_role)
        db.flush()
        print(f"✅ Роль Admin создана: {admin_role.id}")
        
        # Создаём роль "user"
        user_role = Role(
            tenant_id=tenant.id,
            name="User",
            code="user",
            description="Обычный пользователь",
            permissions=["read"],
        )
        db.add(user_role)
        db.flush()
        print(f"✅ Роль User создана: {user_role.id}")
        
        # Создаём пользователя admin
        admin_user = User(
            tenant_id=tenant.id,
            email="admin@test.com",
            password_hash=hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin_user)
        db.flush()
        print(f"✅ Admin user создан: {admin_user.id} (admin@test.com)")
        
        # Создаём membership для admin
        admin_membership = Membership(
            tenant_id=tenant.id,
            user_id=admin_user.id,
            role_id=admin_role.id,
            is_owner=True,
            accepted_at=datetime.utcnow(),
        )
        db.add(admin_membership)
        print(f"✅ Admin membership создан")
        
        # Создаём обычного пользователя
        regular_user = User(
            tenant_id=tenant.id,
            email="user@test.com",
            password_hash=hash_password("user123"),
            first_name="Regular",
            last_name="User",
            is_active=True,
            is_superuser=False,
        )
        db.add(regular_user)
        db.flush()
        print(f"✅ User создан: {regular_user.id} (user@test.com)")
        
        # Создаём membership для user
        regular_membership = Membership(
            tenant_id=tenant.id,
            user_id=regular_user.id,
            role_id=user_role.id,
            is_owner=False,
            accepted_at=datetime.utcnow(),
        )
        db.add(regular_membership)
        print(f"✅ User membership создан")
        
        # Коммитим
        db.commit()
        
        print("\n" + "="*50)
        print("✅ Тестовые данные созданы успешно!")
        print("="*50)
        print("\nТестовые учётные данные:")
        print("  Tenant slug: test-company")
        print("\n  Admin:")
        print("    Email: admin@test.com")
        print("    Password: admin123")
        print("\n  User:")
        print("    Email: user@test.com")
        print("    Password: user123")
        print("="*50)


if __name__ == "__main__":
    seed_data()
