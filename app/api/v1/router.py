from fastapi import APIRouter

from app.api.v1.endpoints import chargers, search, stats

api_router = APIRouter()
api_router.include_router(chargers.router, prefix="/chargers", tags=["chargers"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
