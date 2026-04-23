from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import TankCreate, TankResponse, TankUpdate, TankMeasurementResponse
from app.services import TankService
from app.utils.auth import get_current_user, require_role
from app.models import UserRole
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/tanks", tags=["Tanks"])


@router.get("", response_model=List[TankResponse])
async def get_tanks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all active tanks"""
    tanks = await TankService.get_all(db, skip, limit)
    return tanks


@router.get("/{tank_id}", response_model=TankResponse)
async def get_tank(
    tank_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get tank by ID"""
    tank = await TankService.get_by_id(db, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return tank


@router.post("", response_model=TankResponse, status_code=status.HTTP_201_CREATED)
async def create_tank(
    tank: TankCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.TECH]))
):
    """Create a new tank"""
    from sqlalchemy import select
    from app.models import Tank
    result = await db.execute(select(Tank).where(Tank.name == tank.name))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Tank with this name already exists")
    
    db_tank = await TankService.create(db, tank)
    logger.info("tank_created", tank_id=db_tank.id, name=db_tank.name)
    return db_tank


@router.put("/{tank_id}", response_model=TankResponse)
async def update_tank(
    tank_id: int,
    tank_update: TankUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.TECH]))
):
    """Update tank"""
    updated_tank = await TankService.update(db, tank_id, tank_update)
    if not updated_tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    
    logger.info("tank_updated", tank_id=tank_id)
    return updated_tank


@router.get("/{tank_id}/measurements", response_model=List[TankMeasurementResponse])
async def get_tank_measurements(
    tank_id: int,
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get tank measurements for the last N hours"""
    measurements = await TankService.get_measurements(db, tank_id, hours)
    return measurements


@router.get("/alerts/critical", response_model=List[TankResponse])
async def get_critical_tanks(
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get tanks with critical levels or temperature"""
    critical_tanks = await TankService.get_critical_tanks(db)
    return critical_tanks
