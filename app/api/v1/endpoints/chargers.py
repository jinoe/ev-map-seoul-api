from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.db.mongodb import get_db
from app.schemas.charger import DistrictListResponse, StationListResponse
from app.services import charger_service

router = APIRouter()


@router.get("", response_model=StationListResponse)
def list_chargers(
    limit: int = Query(default=100, le=1000),
    skip: int = Query(default=0, ge=0),
    gu: str | None = Query(default=None, description="구 이름 필터 (예: 강남구)"),
    db: Database = Depends(get_db),
):
    return charger_service.get_stations(db, limit=limit, skip=skip, gu=gu)


@router.get("/districts", response_model=DistrictListResponse)
def list_districts(db: Database = Depends(get_db)):
    return charger_service.get_districts(db)
