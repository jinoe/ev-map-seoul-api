from datetime import datetime
from pydantic import BaseModel


class ChargerInfo(BaseModel):
    chgerId: str
    chgerType: str | None = None
    output: str | None = None
    stat: str | None = None
    statLabel: str | None = None


class StationItem(BaseModel):
    statId: str
    statNm: str | None = None
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None
    busiNm: str | None = None
    chargers: list[ChargerInfo] = []
    totalChargers: int = 0
    availableChargers: int = 0


class StationListResponse(BaseModel):
    stations: list[StationItem]
    total: int


class DistrictSummary(BaseModel):
    name: str
    stations: int
    chargers: int
    available: int


class DistrictListResponse(BaseModel):
    districts: list[DistrictSummary]
    updatedAt: str | None = None


class StatsResponse(BaseModel):
    totalChargers: int
    statusCounts: dict[str, int]
    generatedAt: datetime | None = None
    generatedAtKst: str | None = None
