from fastapi import APIRouter
from app.api.v1.endpoints import farm, market, auth, orders

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(farm.router, prefix="/farms", tags=["Farms"])
api_router.include_router(market.router, prefix="/market", tags=["Market"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"]) 