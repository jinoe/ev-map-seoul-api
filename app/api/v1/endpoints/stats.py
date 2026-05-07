from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from pymongo.database import Database

from app.db.mongodb import get_db
from app.schemas.stats import (
    StatsSummaryResponse,
    StatsOverviewResponse,
    DashboardStatsResponse,
    DistrictStatItem,
    DongStatItem
)
from app.services import stats_service

router = APIRouter()


@router.get("", response_model=StatsSummaryResponse)
def get_stats_summary(db: Database = Depends(get_db)):
    result = stats_service.get_stats_summary(db)
    if not result:
        raise HTTPException(status_code=404, detail="통계 데이터가 없습니다")
    return result


@router.get("/overview", response_model=StatsOverviewResponse)
def get_stats_overview(
    gu: Optional[str] = Query(None),
    dong: Optional[str] = Query(None),
    at: Optional[datetime] = Query(None),
    db: Database = Depends(get_db)
):
    return stats_service.get_stats_overview(db, gu=gu, dong=dong, at=at)


@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    gu: Optional[str] = Query(None),
    dong: Optional[str] = Query(None),
    at: Optional[datetime] = Query(None),
    db: Database = Depends(get_db)
):
    return stats_service.get_dashboard_stats(db, gu=gu, dong=dong, at=at)


@router.get("/districts", response_model=List[DistrictStatItem])
def get_districts_stats(
    at: Optional[datetime] = Query(None),
    db: Database = Depends(get_db)
):
    return stats_service.get_districts_stats(db, at=at)


@router.get("/districts/{gu}/dongs", response_model=List[DongStatItem])
def get_dongs_stats(
    gu: str,
    at: Optional[datetime] = Query(None),
    db: Database = Depends(get_db)
):
    return stats_service.get_dongs_stats(db, gu=gu, at=at)
