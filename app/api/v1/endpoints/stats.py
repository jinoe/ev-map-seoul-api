from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.db.mongodb import get_db
from app.schemas.charger import StatsResponse
from app.services import charger_service

router = APIRouter()


@router.get("", response_model=StatsResponse)
def get_stats(db: Database = Depends(get_db)):
    result = charger_service.get_stats(db)
    if not result:
        raise HTTPException(status_code=404, detail="통계 데이터가 없습니다")
    return result
