from fastapi import APIRouter
from app.api.v1.endpoints import auth, products, tanks, operations, logistics, dashboard, audit

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(tanks.router)
api_router.include_router(operations.router)
api_router.include_router(logistics.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
