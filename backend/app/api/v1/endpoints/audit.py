from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import AuditLogResponse
from app.utils.auth import get_current_user, require_role
from app.models import UserRole, AuditLog
from sqlalchemy import select, desc
from datetime import datetime, timedelta

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    entity_type: str = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.AUDITOR]))
):
    """Get audit logs with optional filters"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(AuditLog).where(AuditLog.timestamp >= cutoff_date).order_by(desc(AuditLog.timestamp))
    
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = list(result.scalars().all())
    
    return logs
