from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import DashboardSummary, TankAlert
from app.services import TankService, ProductService, ReceiptService, ConsumptionService
from app.utils.auth import get_current_user
from app.models import Tank, Product, Receipt, Consumption
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Get dashboard summary with key metrics"""
    # Get total products
    result = await db.execute(select(func.count(Product.id)).where(Product.is_active == True))
    total_products = result.scalar() or 0
    
    # Get total tanks
    result = await db.execute(select(func.count(Tank.id)).where(Tank.is_active == True))
    total_tanks = result.scalar() or 0
    
    # Get total volume
    result = await db.execute(select(func.sum(Tank.current_volume)))
    total_volume = result.scalar() or 0.0
    
    # Get critical tanks
    critical_tanks_result = await db.execute(
        select(Tank).where(
            and_(
                Tank.is_active == True,
                (Tank.level_percent > 90) | (Tank.level_percent < 10)
            )
        ).limit(5)
    )
    critical_tanks = [
        {
            "tank_id": t.id,
            "tank_name": t.name,
            "level_percent": t.level_percent,
            "current_volume": t.current_volume
        }
        for t in critical_tanks_result.scalars().all()
    ]
    
    # Get recent receipts count (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(func.count(Receipt.id)).where(
            and_(
                Receipt.is_deleted == False,
                Receipt.created_at >= week_ago
            )
        )
    )
    recent_receipts = result.scalar() or 0
    
    # Get recent consumptions count (last 7 days)
    result = await db.execute(
        select(func.count(Consumption.id)).where(
            and_(
                Consumption.is_deleted == False,
                Consumption.created_at >= week_ago
            )
        )
    )
    recent_consumptions = result.scalar() or 0
    
    return {
        "total_products": total_products,
        "total_tanks": total_tanks,
        "total_volume_m3": round(total_volume, 2),
        "critical_tanks": critical_tanks,
        "recent_receipts": recent_receipts,
        "recent_consumptions": recent_consumptions
    }


@router.get("/alerts", response_model=List[TankAlert])
async def get_tank_alerts(
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Get all tank alerts"""
    alerts = []
    
    # Get tanks with high level (>90%)
    high_level_result = await db.execute(
        select(Tank).where(and_(Tank.is_active == True, Tank.level_percent > 90))
    )
    for tank in high_level_result.scalars().all():
        alerts.append({
            "tank_id": tank.id,
            "tank_name": tank.name,
            "alert_type": "high_level",
            "current_value": tank.level_percent,
            "threshold_value": 90.0
        })
    
    # Get tanks with low level (<10%)
    low_level_result = await db.execute(
        select(Tank).where(and_(Tank.is_active == True, Tank.level_percent < 10))
    )
    for tank in low_level_result.scalars().all():
        alerts.append({
            "tank_id": tank.id,
            "tank_name": tank.name,
            "alert_type": "low_level",
            "current_value": tank.level_percent,
            "threshold_value": 10.0
        })
    
    # Get tanks with high temperature (>50°C)
    high_temp_result = await db.execute(
        select(Tank).where(
            and_(
                Tank.is_active == True,
                Tank.temperature_celsius != None,
                Tank.temperature_celsius > 50
            )
        )
    )
    for tank in high_temp_result.scalars().all():
        alerts.append({
            "tank_id": tank.id,
            "tank_name": tank.name,
            "alert_type": "high_temperature",
            "current_value": tank.temperature_celsius,
            "threshold_value": 50.0
        })
    
    return alerts
