from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import OrderCreate, OrderResponse, OrderUpdate, WaybillCreate, WaybillResponse
from app.utils.auth import get_current_user, require_role
from app.models import UserRole, Order, Waybill, Vehicle
from app.services import TankService
import structlog
from datetime import datetime
from sqlalchemy import select, func

logger = structlog.get_logger()
router = APIRouter(prefix="/logistics", tags=["Logistics"])


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.LOGISTICIAN]))
):
    """Create a new shipping order"""
    from app.models import Order as OrderModel
    
    # Check if tank has enough volume
    if order.tank_id:
        tank = await TankService.get_by_id(db, order.tank_id)
        if not tank or tank.current_volume < order.requested_volume_m3:
            raise HTTPException(status_code=400, detail="Insufficient tank volume")
    
    # Generate order number
    result = await db.execute(select(func.count(OrderModel.id)))
    count = result.scalar()
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{count + 1:04d}"
    
    db_order = OrderModel(
        order_number=order_number,
        customer_name=order.customer_name,
        product_id=order.product_id,
        requested_volume_m3=order.requested_volume_m3,
        tank_id=order.tank_id,
        status="created",
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    logger.info("order_created", order_id=db_order.id, order_number=db_order.order_number)
    return db_order


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all orders with optional status filter"""
    query = select(Order).offset(skip).limit(limit)
    
    if status_filter:
        query = query.where(Order.status == status_filter)
    
    result = await db.execute(query)
    orders = list(result.scalars().all())
    return orders


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.LOGISTICIAN]))
):
    """Update order status"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    logger.info("order_updated", order_id=order_id)
    return order


@router.post("/waybills", response_model=WaybillResponse, status_code=status.HTTP_201_CREATED)
async def create_waybill(
    waybill: WaybillCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.LOGISTICIAN]))
):
    """Create a waybill for an order"""
    from app.models import Waybill as WaybillModel
    
    # Generate waybill number
    result = await db.execute(select(func.count(WaybillModel.id)))
    count = result.scalar()
    waybill_number = f"WB-{datetime.utcnow().strftime('%Y%m%d')}-{count + 1:04d}"
    
    db_waybill = WaybillModel(
        waybill_number=waybill_number,
        order_id=waybill.order_id,
        vehicle_id=waybill.vehicle_id,
        loaded_volume_m3=waybill.loaded_volume_m3,
        loaded_mass_kg=waybill.loaded_mass_kg
    )
    
    db.add(db_waybill)
    
    # Update order status to shipped
    order_result = await db.execute(select(Order).where(Order.id == waybill.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "shipped"
    
    await db.commit()
    await db.refresh(db_waybill)
    
    logger.info("waybill_created", waybill_id=db_waybill.id, waybill_number=db_waybill.waybill_number)
    return db_waybill


@router.get("/waybills", response_model=List[WaybillResponse])
async def get_waybills(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all waybills"""
    result = await db.execute(select(Waybill).offset(skip).limit(limit))
    waybills = list(result.scalars().all())
    return waybills
