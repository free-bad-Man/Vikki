"""
Test router для проверки tenant isolation и RBAC.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role
from app.dependencies.auth import (
    get_current_user,
    get_tenant_context,
    get_current_user_with_membership,
    require_permission,
)


router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/tenant-info")
async def get_tenant_info(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
):
    """
    Получить информацию о текущем tenant.
    Требует валидный JWT токен.
    """
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "user_id": current_user.id,
        "user_email": current_user.email,
    }


@router.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    membership = Depends(get_current_user_with_membership),
):
    """
    Защищённый endpoint с проверкой membership.
    Требует:
    - Валидный JWT токен
    - Активный membership в tenant
    """
    return {
        "message": "Access granted",
        "tenant_slug": tenant.slug,
        "user_email": current_user.email,
        "role_id": membership.role_id,
        "is_owner": membership.is_owner,
    }


@router.get("/admin-only")
async def admin_only_endpoint(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    role: Role = Depends(require_permission("admin.access")),
):
    """
    Endpoint только для администраторов.
    Требует право "admin.access".
    """
    return {
        "message": "Admin access granted",
        "user_email": current_user.email,
        "role_code": role.code,
        "permissions": role.permissions,
    }


@router.get("/read-only")
async def read_only_endpoint(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant_context),
    role: Role = Depends(require_permission("read")),
):
    """
    Endpoint с правом на чтение.
    Требует право "read".
    """
    return {
        "message": "Read access granted",
        "user_email": current_user.email,
        "role_code": role.code,
    }
