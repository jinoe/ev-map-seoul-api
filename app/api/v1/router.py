from fastapi import APIRouter

from app.api.v1.endpoints import chargers, stats

api_router = APIRouter()
api_router.include_router(chargers.router, prefix="/chargers", tags=["chargers"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
