import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Optional

from pymongo.database import Database

from app.schemas.stats import (
    DashboardStatsResponse,
    DistrictStatItem,
    DongStatItem,
    LongOccupancyItem,
    LongOccupancyStats,
    ScopeInfo,
    StatsOverviewResponse,
    StatsSummaryResponse,
)

KST = timezone(timedelta(hours=9))

GEOJSON_URL = (
    "https://raw.githubusercontent.com/raqoon886/Local_HangJeongDong/master/"
    "hangjeongdong_%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C.geojson"
)

@lru_cache(maxsize=1)
def _get_seoul_geojson():
    """서울시 행정동 GeoJSON 데이터를 로드하여 캐싱."""
    try:
        import httpx
        with httpx.Client() as client:
            resp = client.get(GEOJSON_URL)
            return resp.json()
    except Exception as e:
        print(f"Failed to load GeoJSON: {e}")
        return None

def _is_point_in_polygon(lat: float, lng: float, polygon: list) -> bool:
    """점(lat, lng)이 폴리곤 내부에 있는지 판별 (Ray-casting algorithm)."""
    inside = False
    for i in range(len(polygon)):
        j = i - 1
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
    return inside

def _is_point_in_feature(lat: float, lng: float, geometry: dict) -> bool:
    """MultiPolygon 및 Polygon 처리."""
    g_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if g_type == "Polygon":
        return _is_point_in_polygon(lat, lng, coords[0])
    if g_type == "MultiPolygon":
        return any(_is_point_in_polygon(lat, lng, poly[0]) for poly in coords)
    return False

STATUS_MAP = {
    "0": "알수없음",
    "1": "통신이상",
    "2": "사용가능",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "9": "알수없음",
}
FAULT_STATUSES = {"1", "4", "5"}
WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
FAST_LONG_OCCUPANCY_THRESHOLD_MINUTES = 60
SLOW_LONG_OCCUPANCY_THRESHOLD_MINUTES = 14 * 60
# 삭제
# MAX_LONG_OCCUPANCY_MINUTES = 7 * 24 * 60  # 7일 초과는 데이터 오류로 간주
  
# 추가
FAST_MAX_OCCUPANCY_MINUTES = 4 * 60    # 240분 초과 시 통신이상으로 간주
SLOW_MAX_OCCUPANCY_MINUTES = 24 * 60   # 1440분 초과 시 통신이상으로 간주

SLOW_CHARGER_TYPE_CODES = {"02", "08"}
FAST_CHARGER_TYPE_CODES = {"01", "03", "04", "05", "06", "07", "09", "10"}

def _charger_speed_type(row: dict[str, Any]) -> str:
    """
    장기 점유 기준 적용을 위한 충전기 속도 분류.
    1순위: chgerType 코드
    2순위: output 값 fallback
    """
    chger_type = _normalize_text(row.get("chgerType"))

    if chger_type in SLOW_CHARGER_TYPE_CODES:
        return "slow"

    if chger_type in FAST_CHARGER_TYPE_CODES:
        return "fast"

    # 타입 코드가 없거나 알 수 없는 경우 output으로 보조 판단
    output_value = safe_float(row.get("output"))
    if output_value >= 50:
        return "fast"

    return "slow"


def _long_occupancy_threshold_minutes(row: dict[str, Any]) -> int:
    speed_type = _charger_speed_type(row)

    if speed_type == "fast":
        return FAST_LONG_OCCUPANCY_THRESHOLD_MINUTES

    return SLOW_LONG_OCCUPANCY_THRESHOLD_MINUTES

def _long_occupancy_max_minutes(row: dict[str, Any]) -> int:
      speed_type = _charger_speed_type(row)
      if speed_type == "fast":
          return FAST_MAX_OCCUPANCY_MINUTES
      return SLOW_MAX_OCCUPANCY_MINUTES



def _as_utc_naive(dt: datetime | None) -> datetime | None:
    """MongoDB에 저장된 UTC datetime과 비교하기 위한 안전 변환."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _to_kst(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


def _iso_kst(dt: datetime | None, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    kst = _to_kst(dt)
    return kst.isoformat(timespec="seconds") if kst else None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_float(value: Any) -> float:
    """문자/빈값/단위가 섞인 output 값을 안전하게 float로 변환."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    try:
        return float(match.group(0))
    except ValueError:
        return 0.0


def extract_gu(addr: str | None, zscode: str | None = None) -> str:
    if not addr:
        return "구 미상"
    for part in str(addr).replace(",", " ").split():
        if part.endswith("구") and len(part) > 1:
            return part
    return "구 미상"


def extract_dong(addr: str | None) -> str:
    """도로명주소/지번주소에서 행정동 또는 법정동으로 보이는 토큰 추출."""
    if not addr:
        return "동 미상"
    text = str(addr)

    # 예: 서울특별시 강남구 테헤란로 123 (역삼동)
    paren_matches = re.findall(r"\(([^)]*)\)", text)
    for chunk in paren_matches:
        for token in re.split(r"[\s,]+", chunk):
            token = token.strip()
            if re.search(r"(동|가)$", token) and len(token) > 1:
                return token

    # 예: 서울특별시 강남구 역삼동 123-4
    for token in re.split(r"[\s,()]+", text):
        token = token.strip()
        if re.search(r"(동|가)$", token) and len(token) > 1:
            return token

    return "동 미상"


def _master_match(gu: str | None = None, dong: str | None = None) -> dict[str, Any]:
    match: dict[str, Any] = {"delYn": {"$ne": "Y"}}
    addr_conditions = []
    if gu:
        addr_conditions.append({"addr": {"$regex": re.escape(gu.strip())}})
    if len(addr_conditions) == 1:
        match.update(addr_conditions[0])
    elif len(addr_conditions) > 1:
        match = {"$and": [match, *addr_conditions]}
    return match


def get_latest_bucket(db: Database, at: datetime | None = None) -> Optional[dict]:
    """기준 시각 이전의 가장 최근 상태 스냅샷 문서 1개를 반환."""
    query: dict[str, Any] = {}
    at_utc = _as_utc_naive(at)
    if at_utc:
        query["collectedAtBucket"] = {"$lte": at_utc}

    latest = db.charger_status_snapshot.find_one(
        query,
        sort=[("collectedAtBucket", -1), ("collectedAt", -1)],
    )
    if latest is None and at_utc:
        # 과거 데이터에 collectedAtBucket이 없거나 타입이 섞인 경우를 위한 폴백
        latest = db.charger_status_snapshot.find_one(
            {"collectedAt": {"$lte": at_utc}},
            sort=[("collectedAt", -1)],
        )
    return latest


def _status_docs_for_bucket(db: Database, bucket: datetime | None) -> dict[tuple[str, str], dict[str, Any]]:
    if bucket is None:
        return {}
    cursor = db.charger_status_snapshot.find(
        {"collectedAtBucket": bucket},
        {
            "_id": 0,
            "statId": 1,
            "chgerId": 1,
            "stat": 1,
            "statUpdDt": 1,
            "nowTsdt": 1,
            "lastTsdt": 1,
            "lastTedt": 1,
            "collectedAt": 1,
            "collectedAtKst": 1,
            "raw": 1,
        },
    )
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for doc in cursor:
        stat_id = _normalize_text(doc.get("statId"))
        chger_id = _normalize_text(doc.get("chgerId"))
        if stat_id and chger_id:
            result[(stat_id, chger_id)] = doc
    return result


def _current_status_from_current(db: Database) -> dict[tuple[str, str], dict[str, Any]]:
    """charger_current 컬렉션에서 모든 충전기의 최신 상태를 가져옴."""
    cursor = db.charger_current.find(
        {},
        {
            "_id": 0,
            "statId": 1,
            "chgerId": 1,
            "stat": 1,
            "statUpdDt": 1,
            "updatedAt": 1,
            "lastObservedAt": 1,
            "raw": 1,
        },
    )
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for doc in cursor:
        stat_id = _normalize_text(doc.get("statId"))
        chger_id = _normalize_text(doc.get("chgerId"))
        if stat_id and chger_id:
            result[(stat_id, chger_id)] = doc
    return result


def _current_rows(
    db: Database,
    gu: str | None = None,
    dong: str | None = None,
    at: datetime | None = None,
) -> tuple[list[dict[str, Any]], Optional[dict], dict[tuple[str, str], dict[str, Any]]]:
    # --- 기존 스냅샷 방식 (주석 처리) ---
    # latest = get_latest_bucket(db, at)
    # bucket = latest.get("collectedAtBucket") if latest else None
    # status_docs = _status_docs_for_bucket(db, bucket)
    # --------------------------------

    if at is None:
        # 실시간: charger_current 사용
        status_docs = _current_status_from_current(db)
        # 최신 업데이트 시각 산출을 위해 가상의 latest 객체 생성
        latest_doc = db.charger_current.find_one({}, sort=[("updatedAt", -1)])
        latest = {
            "collectedAt": latest_doc.get("updatedAt") if latest_doc else datetime.now(timezone.utc),
            "collectedAtKst": latest_doc.get("lastObservedAtKst") if latest_doc else None
        }
    else:
        # 과거 시점 조회: 기존 스냅샷 방식 사용
        latest = get_latest_bucket(db, at)
        bucket = latest.get("collectedAtBucket") if latest else None
        status_docs = _status_docs_for_bucket(db, bucket)

    # 동 필터가 있는 경우 해당 동의 Geometry 정보 찾기 (지도와 로직 일치)
    target_geometry = None
    if gu and dong:
        geojson = _get_seoul_geojson()
        if geojson:
            for feature in geojson.get("features", []):
                props = feature.get("properties", {})
                f_gu = props.get("sggnm")
                f_dong = props.get("adm_nm", "").split()[-1]
                if f_gu == gu and f_dong == dong:
                    target_geometry = feature.get("geometry")
                    break

    projection = {
        "_id": 0,
        "statId": 1,
        "chgerId": 1,
        "statNm": 1,
        "addr": 1,
        "lat": 1,
        "lng": 1,
        "chgerType": 1,
        "output": 1,
        "kind": 1,
        "kindDetail": 1,
        "busiNm": 1,
        "busiId": 1,
        "raw": 1,
    }

    rows: list[dict[str, Any]] = []
    for master in db.charger_master.find(_master_match(gu=gu), projection):
        # 좌표 기반 동 필터링 적용 (동 선택 시)
        if target_geometry:
            lat = master.get("lat")
            lng = master.get("lng")
            if lat is None or lng is None:
                continue
            # lat/lng 순서 주의 (GeoJSON은 [lng, lat], 연산은 lat, lng)
            if not _is_point_in_feature(float(lat), float(lng), target_geometry):
                continue

        stat_id = _normalize_text(master.get("statId"))
        chger_id = _normalize_text(master.get("chgerId"))
        status_doc = status_docs.get((stat_id, chger_id), {}) if stat_id and chger_id else {}
        raw_status = status_doc.get("raw") or {}
        stat = _normalize_text(status_doc.get("stat")) or _normalize_text(raw_status.get("stat"))
        rows.append({**master, "statusDoc": status_doc, "stat": stat})
    return rows, latest, status_docs


def _get_status_ts(status_doc: dict[str, Any], key: str) -> str | None:
    raw = status_doc.get("raw") or {}
    return _normalize_text(status_doc.get(key)) or _normalize_text(raw.get(key))


def _parse_kst_compact_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    except ValueError:
        return None


def _reference_kst(latest: dict | None) -> datetime:
    if latest and latest.get("collectedAt"):
        converted = _to_kst(latest.get("collectedAt"))
        if converted:
            return converted
    return datetime.now(KST)


# def _long_occupancy_item(row: dict[str, Any], latest: dict | None) -> LongOccupancyItem | None:
#     if row.get("stat") != "3":
#         return None
#     status_doc = row.get("statusDoc") or {}
#     started_at = _parse_kst_compact_datetime(_get_status_ts(status_doc, "nowTsdt"))
#     if not started_at:
#         return None
#     duration = int((_reference_kst(latest) - started_at).total_seconds() // 60)

#     threshold_minutes = _long_occupancy_threshold_minutes(row)

#     if duration < threshold_minutes or duration > MAX_LONG_OCCUPANCY_MINUTES:
#         return None
#     return LongOccupancyItem(
#         statId=row.get("statId"),
#         chgerId=row.get("chgerId"),
#         statNm=row.get("statNm"),
#         addr=row.get("addr"),
#         gu=extract_gu(row.get("addr")),
#         dong=extract_dong(row.get("addr")),
#         output=row.get("output"),
#         nowTsdt=_get_status_ts(status_doc, "nowTsdt"),
#         durationMinutes=max(duration, 0),
#         lat=row.get("lat"),
#         lng=row.get("lng"),
#     )

def _long_occupancy_item(row: dict[str, Any], latest: dict | None) -> LongOccupancyItem | None:
    if row.get("stat") != "3":
        return None
    status_doc = row.get("statusDoc") or {}
    
    # 조건 1: lastTedt > lastTsdt → 충전 종료됐으나 상태 미갱신 (통신이상)
    last_tsdt = _parse_kst_compact_datetime(_get_status_ts(status_doc, "lastTsdt"))
    last_tedt = _parse_kst_compact_datetime(_get_status_ts(status_doc, "lastTedt"))
    if last_tsdt and last_tedt and last_tedt > last_tsdt:
        return None
        
    started_at = _parse_kst_compact_datetime(_get_status_ts(status_doc, "nowTsdt"))
    if not started_at:
        return None
    duration = int((_reference_kst(latest) - started_at).total_seconds() // 60)
    
    threshold_minutes = _long_occupancy_threshold_minutes(row)
    max_minutes = _long_occupancy_max_minutes(row)
    
    if duration < threshold_minutes or duration > max_minutes:
        return None
    return LongOccupancyItem(
        statId=row.get("statId"),
        chgerId=row.get("chgerId"),
        statNm=row.get("statNm"),
        addr=row.get("addr"),
        gu=extract_gu(row.get("addr")),
        dong=extract_dong(row.get("addr")),
        output=row.get("output"),
        speedType=_charger_speed_type(row),
        nowTsdt=_get_status_ts(status_doc, "nowTsdt"),
        durationMinutes=max(duration, 0),
        lat=row.get("lat"),
        lng=row.get("lng"),
    )

def _overview_from_rows(
    rows: list[dict[str, Any]],
    latest: dict | None,
    gu: str | None = None,
    dong: str | None = None,
) -> StatsOverviewResponse:
    total_chargers = len(rows)
    stations: set[str] = set()

    available_count = charging_count = fault_count = 0
    maintenance_count = stopped_count = communication_error_count = unknown_count = 0
    rapid_chargers = slow_chargers = ultra_fast_chargers = 0

    outputs: list[float] = []
    long_occupancy_items: list[LongOccupancyItem] = []
    status_distribution: dict[str, int] = defaultdict(int)
    charger_type_distribution: dict[str, int] = defaultdict(int)
    facility_distribution: dict[str, int] = defaultdict(int)

    for row in rows:
        stat_id = row.get("statId")
        if stat_id:
            stations.add(stat_id)

        stat = row.get("stat")
        if stat == "2":
            available_count += 1
        elif stat == "3":
            charging_count += 1
        elif stat == "1":
            communication_error_count += 1
        elif stat == "4":
            stopped_count += 1
        elif stat == "5":
            maintenance_count += 1
        else:
            unknown_count += 1

        if stat in FAULT_STATUSES:
            fault_count += 1

        status_distribution[STATUS_MAP.get(stat, "알수없음")] += 1

        output_value = safe_float(row.get("output"))
        if output_value >= 200:
            ultra_fast_chargers += 1
            charger_type_distribution["초급속"] += 1
        elif output_value >= 50:
            rapid_chargers += 1
            charger_type_distribution["급속"] += 1
        else:
            slow_chargers += 1
            charger_type_distribution["완속"] += 1
        if output_value > 0:
            outputs.append(output_value)

        raw = row.get("raw") or {}
        facility_key = row.get("kind") or raw.get("kind") or row.get("kindDetail") or raw.get("kindDetail") or "기타"
        facility_distribution[str(facility_key)] += 1

        item = _long_occupancy_item(row, latest)
        if item:
            long_occupancy_items.append(item)

    long_occupancy_items.sort(key=lambda item: item.durationMinutes, reverse=True)

    fast_items = [i for i in long_occupancy_items if i.speedType == "fast"]
    slow_items = [i for i in long_occupancy_items if i.speedType == "slow"]

    return StatsOverviewResponse(
        scope=ScopeInfo(gu=gu, dong=dong),
        updatedAt=_iso_kst(latest.get("collectedAt") if latest else None, latest.get("collectedAtKst") if latest else None),
        totalChargers=total_chargers,
        totalStations=len(stations),
        rapidChargers=rapid_chargers,
        slowChargers=slow_chargers,
        ultraFastChargers=ultra_fast_chargers,
        availableCount=available_count,
        chargingCount=charging_count,
        faultCount=fault_count,
        maintenanceCount=maintenance_count,
        stoppedCount=stopped_count,
        communicationErrorCount=communication_error_count,
        unknownCount=unknown_count,
        availabilityRate=round((available_count / total_chargers * 100), 2) if total_chargers else 0,
        avgOutput=round(sum(outputs) / len(outputs), 2) if outputs else 0,
        maxOutput=max(outputs) if outputs else 0,
        longOccupancy=LongOccupancyStats(
            count=len(long_occupancy_items),
            fastCount=len(fast_items),
            slowCount=len(slow_items),
            thresholdMinutes=None,
            thresholdMinutesByType={
                "급속": FAST_LONG_OCCUPANCY_THRESHOLD_MINUTES,
                "완속": SLOW_LONG_OCCUPANCY_THRESHOLD_MINUTES,
            },
            items=long_occupancy_items[:20],
            fastItems=fast_items[:20],
            slowItems=slow_items[:20],
        ),
        statusDistribution=dict(status_distribution),
        chargerTypeDistribution=dict(charger_type_distribution),
        facilityDistribution=dict(facility_distribution),
    )


def get_stats_summary(db: Database) -> Optional[StatsSummaryResponse]:
    # --- 기존 스냅샷 방식 (주석 처리) ---
    # latest = get_latest_bucket(db)
    # if not latest:
    #     return None
    # bucket = latest.get("collectedAtBucket")
    # pipeline = [
    #     {"$match": {"collectedAtBucket": bucket}},
    #     {"$group": {"_id": "$stat", "count": {"$sum": 1}}},
    # ]
    # status_counts_raw = {
    #     str(doc.get("_id") or "0"): doc.get("count", 0)
    #     for doc in db.charger_status_snapshot.aggregate(pipeline)
    # }
    # --------------------------------

    # charger_current 기반 실시간 집계
    pipeline = [
        {"$group": {"_id": "$stat", "count": {"$sum": 1}}},
    ]
    status_counts_raw = {
        str(doc.get("_id") or "0"): doc.get("count", 0)
        for doc in db.charger_current.aggregate(pipeline)
    }
    
    latest_doc = db.charger_current.find_one({}, sort=[("updatedAt", -1)])
    if not latest_doc:
        return None

    total_chargers = sum(status_counts_raw.values())
    available_count = status_counts_raw.get("2", 0)
    charging_count = status_counts_raw.get("3", 0)
    fault_count = sum(status_counts_raw.get(s, 0) for s in FAULT_STATUSES)
    unknown_count = status_counts_raw.get("0", 0) + status_counts_raw.get("9", 0) + status_counts_raw.get("None", 0)
    total_stations = len(db.charger_master.distinct("statId", {"delYn": {"$ne": "Y"}}))

    return StatsSummaryResponse(
        totalChargers=total_chargers,
        totalStations=total_stations,
        statusCounts=status_counts_raw,
        availableCount=available_count,
        chargingCount=charging_count,
        faultCount=fault_count,
        unknownCount=unknown_count,
        availabilityRate=round((available_count / total_chargers * 100), 2) if total_chargers else 0,
        generatedAt=latest_doc.get("updatedAt"),
        generatedAtKst=_iso_kst(latest_doc.get("updatedAt"), latest_doc.get("lastObservedAtKst")),
        collectedAtBucket=latest_doc.get("lastSnapshotBucket").isoformat() if latest_doc.get("lastSnapshotBucket") else None,
    )


def get_stats_overview(
    db: Database,
    gu: str | None = None,
    dong: str | None = None,
    at: datetime | None = None,
) -> StatsOverviewResponse:
    rows, latest, _ = _current_rows(db, gu=gu, dong=dong, at=at)
    return _overview_from_rows(rows, latest, gu=gu, dong=dong)


def _group_current_rows(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = extract_gu(row.get("addr")) if group_key == "gu" else extract_dong(row.get("addr"))
        grouped[key].append(row)
    result = []
    for key, group_rows in grouped.items():
        stations = {r.get("statId") for r in group_rows if r.get("statId")}
        chargers = len(group_rows)
        available = sum(1 for r in group_rows if r.get("stat") == "2")
        charging = sum(1 for r in group_rows if r.get("stat") == "3")
        fault = sum(1 for r in group_rows if r.get("stat") in FAULT_STATUSES)
        outputs = [safe_float(r.get("output")) for r in group_rows if safe_float(r.get("output")) > 0]
        rapid = sum(1 for r in group_rows if 50 <= safe_float(r.get("output")) < 200)
        slow = sum(1 for r in group_rows if safe_float(r.get("output")) < 50)
        ultra = sum(1 for r in group_rows if safe_float(r.get("output")) >= 200)
        result.append(
            {
                "key": key,
                "stations": len(stations),
                "chargers": chargers,
                "available": available,
                "charging": charging,
                "fault": fault,
                "availabilityRate": round((available / chargers * 100), 2) if chargers else 0,
                "avgOutput": round(sum(outputs) / len(outputs), 2) if outputs else 0,
                "rapidChargers": rapid,
                "slowChargers": slow,
                "ultraFastChargers": ultra,
            }
        )
    return sorted(result, key=lambda x: (-x["chargers"], x["key"]))


def get_districts_stats(db: Database, at: datetime | None = None) -> list[DistrictStatItem]:
    rows, _, _ = _current_rows(db, at=at)
    return [
        DistrictStatItem(
            gu=item["key"],
            stations=item["stations"],
            chargers=item["chargers"],
            available=item["available"],
            charging=item["charging"],
            fault=item["fault"],
            availabilityRate=item["availabilityRate"],
            avgOutput=item["avgOutput"],
            rapidChargers=item["rapidChargers"],
            slowChargers=item["slowChargers"],
            ultraFastChargers=item["ultraFastChargers"],
        )
        for item in _group_current_rows(rows, "gu")
        if item["key"] != "구 미상"
    ]


def get_dongs_stats(db: Database, gu: str, at: datetime | None = None) -> list[DongStatItem]:
    rows, _, _ = _current_rows(db, gu=gu, at=at)
    return [
        DongStatItem(
            dong=item["key"],
            stations=item["stations"],
            chargers=item["chargers"],
            available=item["available"],
            charging=item["charging"],
            fault=item["fault"],
            availabilityRate=item["availabilityRate"],
            avgOutput=item["avgOutput"],
            rapidChargers=item["rapidChargers"],
            slowChargers=item["slowChargers"],
            ultraFastChargers=item["ultraFastChargers"],
        )
        for item in _group_current_rows(rows, "dong")
        if item["key"] != "동 미상"
    ]


def _top_group_fault_rate(rows: list[dict[str, Any]], field_getter, limit: int = 10) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "fault": 0})
    for row in rows:
        name = field_getter(row) or "미상"
        grouped[str(name)]["total"] += 1
        if row.get("stat") in FAULT_STATUSES:
            grouped[str(name)]["fault"] += 1
    items = [
        {"name": name, "total": v["total"], "fault": v["fault"], "rate": round(v["fault"] / v["total"] * 100, 2) if v["total"] else 0}
        for name, v in grouped.items()
    ]
    return sorted(items, key=lambda x: (-x["fault"], -x["total"], x["name"]))[:limit]


def _install_year_fault_rate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "fault": 0})
    for row in rows:
        raw = row.get("raw") or {}
        year = _normalize_text(raw.get("year")) or "미상"
        grouped[year]["total"] += 1
        if row.get("stat") in FAULT_STATUSES:
            grouped[year]["fault"] += 1
    return [
        {"year": year, "total": v["total"], "fault": v["fault"], "rate": round(v["fault"] / v["total"] * 100, 2) if v["total"] else 0}
        for year, v in sorted(grouped.items(), key=lambda kv: kv[0])
    ]


def _status_history_rows(db: Database, latest: dict | None, days: int = 7) -> list[dict[str, Any]]:
    if not latest or not latest.get("collectedAtBucket"):
        return []
    end = latest["collectedAtBucket"]
    start = end - timedelta(days=days)
    cursor = db.charger_status_snapshot.find(
        {"collectedAtBucket": {"$gte": start, "$lte": end}},
        {"_id": 0, "stat": 1, "collectedAtBucket": 1, "raw": 1},
    )
    return list(cursor)


def _availability_by_weekday(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, int]] = defaultdict(lambda: {"total": 0, "available": 0})
    for row in history:
        bucket = row.get("collectedAtBucket")
        kst = _to_kst(bucket)
        if not kst:
            continue
        weekday = kst.weekday()
        grouped[weekday]["total"] += 1
        if row.get("stat") == "2":
            grouped[weekday]["available"] += 1
    return [
        {
            "day": WEEKDAY_LABELS[idx],
            "rate": round(grouped[idx]["available"] / grouped[idx]["total"] * 100, 2) if grouped[idx]["total"] else 0,
            "total": grouped[idx]["total"],
        }
        for idx in range(7)
    ]


def _availability_heatmap(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: {"total": 0, "available": 0, "charging": 0})
    for row in history:
        bucket = row.get("collectedAtBucket")
        kst = _to_kst(bucket)
        if not kst:
            continue
        key = (kst.weekday(), kst.hour)
        grouped[key]["total"] += 1
        if row.get("stat") == "2":
            grouped[key]["available"] += 1
        if row.get("stat") == "3":
            grouped[key]["charging"] += 1
    items = []
    for weekday in range(7):
        for hour in range(24):
            cell = grouped[(weekday, hour)]
            total = cell["total"]
            items.append(
                {
                    "day": WEEKDAY_LABELS[weekday],
                    "weekday": weekday,
                    "hour": hour,
                    "availabilityRate": round(cell["available"] / total * 100, 2) if total else 0,
                    "chargingRate": round(cell["charging"] / total * 100, 2) if total else 0,
                    "total": total,
                }
            )
    return items


def _weekday_weekend_hourly_usage(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: {"total": 0, "charging": 0})
    for row in history:
        bucket = row.get("collectedAtBucket")
        kst = _to_kst(bucket)
        if not kst:
            continue
        day_type = "weekend" if kst.weekday() >= 5 else "weekday"
        key = (day_type, kst.hour)
        grouped[key]["total"] += 1
        if row.get("stat") == "3":
            grouped[key]["charging"] += 1
    return [
        {
            "type": day_type,
            "hour": hour,
            "chargingCount": grouped[(day_type, hour)]["charging"],
            "chargingRate": round(grouped[(day_type, hour)]["charging"] / grouped[(day_type, hour)]["total"] * 100, 2) if grouped[(day_type, hour)]["total"] else 0,
            "total": grouped[(day_type, hour)]["total"],
        }
        for day_type in ["weekday", "weekend"]
        for hour in range(24)
    ]


def _trend_from_charger_stats(db: Database, latest: dict | None, limit: int = 48) -> list[dict[str, Any]]:
    if not latest:
        return []
    cursor = db.charger_stats.find(
        {"type": "basic_status_snapshot"},
        {"_id": 0, "collectedAtBucket": 1, "statusCounts": 1, "totalChargers": 1},
    ).sort("collectedAtBucket", -1).limit(limit)
    items = []
    for row in cursor:
        counts = row.get("statusCounts") or {}
        total = row.get("totalChargers") or sum(counts.values())
        fault = sum(counts.get(s, 0) for s in FAULT_STATUSES)
        bucket = row.get("collectedAtBucket")
        items.append(
            {
                "time": _iso_kst(bucket),
                "fault": fault,
                "total": total,
                "rate": round(fault / total * 100, 2) if total else 0,
            }
        )
    return list(reversed(items))


def get_dashboard_stats(
    db: Database,
    gu: str | None = None,
    dong: str | None = None,
    at: datetime | None = None,
) -> DashboardStatsResponse:
    rows, latest, _ = _current_rows(db, gu=gu, dong=dong, at=at)
    overview = _overview_from_rows(rows, latest, gu=gu, dong=dong)
    history = _status_history_rows(db, latest, days=7) if not gu and not dong else []

    facility_type_distribution = [
        {"name": name, "value": value}
        for name, value in sorted(overview.facilityDistribution.items(), key=lambda kv: -kv[1])
    ]
    district_ranking = [item.model_dump() for item in get_districts_stats(db, at=at)[:10]] if not gu and not dong else []

    return DashboardStatsResponse(
        kpis={
            "totalChargers": overview.totalChargers,
            "totalStations": overview.totalStations,
            "availabilityRate": overview.availabilityRate,
            "availableCount": overview.availableCount,
            "chargingCount": overview.chargingCount,
            "faultCount": overview.faultCount,
            "longOccupancyCount": overview.longOccupancy.count,
            "updatedAt": overview.updatedAt,
        },
        manufacturerFaultRate=_top_group_fault_rate(rows, lambda r: (r.get("raw") or {}).get("maker") or r.get("busiNm")),
        installYearFaultRate=_install_year_fault_rate(rows),
        availabilityByWeekday=_availability_by_weekday(history),
        availabilityHeatmap=_availability_heatmap(history),
        weekdayWeekendHourlyUsage=_weekday_weekend_hourly_usage(history),
        facilityTypeDistribution=facility_type_distribution,
        facilityTypeCounts=facility_type_distribution,
        faultTrend=_trend_from_charger_stats(db, latest),
        longOccupancyTrend=[],
        districtRanking=district_ranking,
    )
