from fastapi import APIRouter

from app.api.v1.endpoints import chargers

api_router = APIRouter()
api_router.include_router(chargers.router, prefix="/chargers", tags=["chargers"])
