from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import ReceiptCreate, ReceiptResponse, ConsumptionCreate, ConsumptionResponse, BalanceCalculationRequest, BalanceCalculationResponse
from app.services import ReceiptService, ConsumptionService, BalanceCalculatorService
from app.utils.auth import get_current_user, require_role
from app.models import UserRole
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/operations", tags=["Operations"])


@router.post("/receipts", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    receipt: ReceiptCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.STOREKEEPER]))
):
    """Create a new receipt (fuel intake)"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else 1
        db_receipt = await ReceiptService.create_receipt(db, receipt, user_id)
        logger.info("receipt_created", receipt_id=db_receipt.id, receipt_number=db_receipt.receipt_number)
        return db_receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/receipts", response_model=List[ReceiptResponse])
async def get_receipts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all receipts"""
    receipts = await ReceiptService.get_all(db, skip, limit)
    return receipts


@router.post("/consumptions", response_model=ConsumptionResponse, status_code=status.HTTP_201_CREATED)
async def create_consumption(
    consumption: ConsumptionCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.STOREKEEPER]))
):
    """Create a new consumption (fuel usage/shipment)"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else 1
        db_consumption = await ConsumptionService.create_consumption(db, consumption, user_id)
        logger.info("consumption_created", consumption_id=db_consumption.id, consumption_number=db_consumption.consumption_number)
        return db_consumption
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/consumptions", response_model=List[ConsumptionResponse])
async def get_consumptions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all consumptions"""
    consumptions = await ConsumptionService.get_all(db, skip, limit)
    return consumptions


@router.post("/balance/calculate", response_model=BalanceCalculationResponse)
async def calculate_balance(
    balance_request: BalanceCalculationRequest,
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.TECH]))
):
    """Calculate material balance for process units"""
    inputs = [item.model_dump() for item in balance_request.inputs]
    outputs = [item.model_dump() for item in balance_request.outputs]
    
    result = await BalanceCalculatorService.calculate_balance(inputs, outputs)
    
    logger.info("balance_calculated", 
                total_input=result['total_input_kg'], 
                total_output=result['total_output_kg'],
                discrepancy_percent=result['discrepancy_percent'])
    
    return result
