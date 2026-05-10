from datetime import datetime
from typing import Annotated, Union
from pydantic import BaseModel, Discriminator, Field, Tag


class Condition(BaseModel):
    key: str
    op: str    # "==" | "!=" | ">=" | "<=" | ">" | "<"
    value: str


class OrGroup(BaseModel):
    or_: list[Condition] = Field(alias="or")

    model_config = {"populate_by_name": True}


def _discriminate(v: object) -> str:
    if isinstance(v, dict):
        return "or" if "or" in v else "simple"
    if isinstance(v, OrGroup):
        return "or"
    return "simple"


FilterItem = Annotated[
    Union[
        Annotated[OrGroup, Tag("or")],
        Annotated[Condition, Tag("simple")],
    ],
    Discriminator(_discriminate),
]


class SearchRequest(BaseModel):
    filters: list[FilterItem] = []
    limit: int = Field(default=80000, le=100000)
    skip: int = Field(default=0, ge=0)
    at: datetime | None = Field(
        default=None,
        description="조회 기준 시각 (ISO 8601). 이 시각 이전 가장 최근 수집 주기의 충전 상태를 사용합니다.",
    )
    query: str | None = Field(
        default=None,
        description=(
            "복합 조건 문자열. 'AND'·'OR' 로 조건을 연결합니다 (AND 우선). "
            "filters 와 AND 로 결합됩니다. "
            "예: 'stat == 사용가능 AND output >= 50' / '강남역' (충전소명 부분 검색)"
        ),
    )
    fields: list[str] | None = Field(
        default=None,
        description="반환할 MongoDB 필드명 목록. 미지정 시 전체 필드 반환. 예: ['lat', 'lng', 'raw.zscode']",
    )


class ChargerResult(BaseModel):
    statId: str | None = None
    chgerId: str | None = None
    statNm: str | None = None
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None
    busiNm: str | None = None
    chgerType: str | None = None
    chgerTypeLabel: str | None = None
    output: str | None = None
    method: str | None = None
    parkingFree: str | None = None
    limitYn: str | None = None
    delYn: str | None = None
    useTime: str | None = None
    kind: str | None = None
    zcode: str | None = None
    zscode: str | None = None
    stat: str | None = None
    statLabel: str | None = None


class SearchResponse(BaseModel):
    results: list[ChargerResult]
    total: int
    snapshot_bucket: datetime | None = None
    query_debug: dict | None = None
