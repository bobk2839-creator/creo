from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db_session
from app.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.services import ProductService
from app.utils.auth import get_current_user, require_role
from app.models import UserRole
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get all active products"""
    products = await ProductService.get_all(db, skip, limit)
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(get_current_user)
):
    """Get product by ID"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.TECH]))
):
    """Create a new product"""
    # Check if product name already exists
    from sqlalchemy import select
    from app.models import Product
    result = await db.execute(select(Product).where(Product.name == product.name))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    db_product = await ProductService.create(db, product)
    logger.info("product_created", product_id=db_product.id, name=db_product.name)
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.TECH]))
):
    """Update product"""
    updated_product = await ProductService.update(db, product_id, product_update)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info("product_updated", product_id=product_id)
    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserRole = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Soft delete product"""
    success = await ProductService.delete(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info("product_deleted", product_id=product_id)
