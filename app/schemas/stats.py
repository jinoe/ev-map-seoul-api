from datetime import datetime
from typing import Any
from pydantic import BaseModel


class StatusCounts(BaseModel):
    available: int = 0
    charging: int = 0
    fault: int = 0
    unknown: int = 0


class StatsSummaryResponse(BaseModel):
    totalChargers: int
    totalStations: int
    statusCounts: dict[str, int]
    availableCount: int
    chargingCount: int
    faultCount: int
    unknownCount: int
    availabilityRate: float
    generatedAt: datetime | None = None
    generatedAtKst: str | None = None
    collectedAtBucket: str | None = None


class ScopeInfo(BaseModel):
    gu: str | None = None
    dong: str | None = None


class LongOccupancyItem(BaseModel):
    statId: str
    chgerId: str
    statNm: str | None = None
    addr: str | None = None
    gu: str | None = None
    dong: str | None = None
    output: str | None = None
    nowTsdt: str | None = None
    durationMinutes: int
    lat: float | None = None
    lng: float | None = None


class LongOccupancyStats(BaseModel):
    count: int
    thresholdMinutes: int
    items: list[LongOccupancyItem]


class StatsOverviewResponse(BaseModel):
    scope: ScopeInfo
    updatedAt: str | None = None
    totalChargers: int
    totalStations: int
    rapidChargers: int
    slowChargers: int
    ultraFastChargers: int
    availableCount: int
    chargingCount: int
    faultCount: int
    maintenanceCount: int
    stoppedCount: int
    communicationErrorCount: int
    unknownCount: int
    availabilityRate: float
    avgOutput: float
    maxOutput: float
    longOccupancy: LongOccupancyStats
    statusDistribution: dict[str, int]
    chargerTypeDistribution: dict[str, int]
    facilityDistribution: dict[str, int]


class DashboardStatsResponse(BaseModel):
    kpis: dict[str, Any]
    manufacturerFaultRate: list[dict[str, Any]]
    installYearFaultRate: list[dict[str, Any]]
    availabilityByWeekday: list[dict[str, Any]]
    availabilityHeatmap: list[dict[str, Any]]
    weekdayWeekendHourlyUsage: list[dict[str, Any]]
    facilityTypeDistribution: list[dict[str, Any]]
    facilityTypeCounts: list[dict[str, Any]]
    faultTrend: list[dict[str, Any]]
    longOccupancyTrend: list[dict[str, Any]]
    districtRanking: list[dict[str, Any]]


class DistrictStatItem(BaseModel):
    gu: str
    stations: int
    chargers: int
    available: int
    charging: int
    fault: int
    availabilityRate: float
    avgOutput: float
    rapidChargers: int
    slowChargers: int
    ultraFastChargers: int


class DongStatItem(BaseModel):
    dong: str
    stations: int
    chargers: int
    available: int
    charging: int
    fault: int
    availabilityRate: float
    avgOutput: float
    rapidChargers: int
    slowChargers: int
    ultraFastChargers: int
