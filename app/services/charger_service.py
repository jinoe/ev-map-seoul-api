import re
from datetime import datetime, timedelta, timezone

from pymongo.database import Database

from app.schemas.charger import (
    ChargerDetailItem,
    ChargerInfo,
    DistrictListResponse,
    DistrictSummary,
    StationDetailResponse,
    StationItem,
    StationListResponse,
    StatsResponse,
)

KST = timezone(timedelta(hours=9))

STAT_LABELS: dict[str, str] = {
    "0": "알수없음",
    "1": "통신이상",
    "2": "사용가능",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "9": "알수없음",
}

CHGER_TYPE_LABELS: dict[str, str] = {
    "01": "DC차데모",
    "02": "AC완속",
    "03": "DC차데모+AC3상",
    "04": "DC차데모+완속",
    "05": "DC차데모+AC3상+완속",
    "06": "DC콤보",
    "07": "DC차데모+DC콤보",
    "08": "AC3상",
    "09": "DC콤보+완속",
    "10": "수퍼차저",
}

KIND_LABELS: dict[str, str] = {
    "W0": "휴게소", "W1": "마트/쇼핑몰", "W2": "주유소", "W3": "상업시설",
    "G0": "공공시설", "G1": "공용주차장", "G2": "공공건물", "G3": "아파트",
    "A0": "관광지", "J0": "직장/사업장",
}

SLOW_CHGER_TYPE_CODES = {"02", "08"}


def _format_kst_compact(value: str | None) -> str | None:
    if not value or str(value).strip() in ("", "null", "None"):
        return None
    try:
        dt = datetime.strptime(str(value).strip(), "%Y%m%d%H%M%S").replace(tzinfo=KST)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _speed_type(chger_type: str | None, output_raw: str | None) -> str:
    if chger_type in SLOW_CHGER_TYPE_CODES:
        return "slow"
    if chger_type and chger_type in {"01", "03", "04", "05", "06", "07", "09", "10"}:
        return "fast"
    try:
        return "fast" if float(str(output_raw or "0").strip() or "0") >= 50 else "slow"
    except ValueError:
        return "slow"


def _extract_gu(addr: str | None) -> str | None:
    if not addr:
        return None
    for part in addr.split():
        if part.endswith("구"):
            return part
    return None


def _build_status_map(db: Database) -> dict[tuple[str, str], str]:
    latest = db.charger_status_snapshot.find_one(sort=[("collectedAtBucket", -1), ("collectedAt", -1)])
    if not latest:
        return {}
    bucket = latest["collectedAtBucket"]
    return {
        (s["statId"], s["chgerId"]): s.get("stat") or ""
        for s in db.charger_status_snapshot.find(
            {"collectedAtBucket": bucket},
            {"statId": 1, "chgerId": 1, "stat": 1, "_id": 0},
        )
    }


def get_stations(
    db: Database,
    limit: int = 100,
    skip: int = 0,
    gu: str | None = None,
) -> StationListResponse:
    query: dict = {"delYn": {"$ne": "Y"}}
    if gu:
        query["addr"] = {"$regex": re.escape(gu)}

    status_map = _build_status_map(db)

    count_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$statId"}},
        {"$count": "count"},
    ]
    count_result = list(db.charger_master.aggregate(count_pipeline))
    station_total = count_result[0]["count"] if count_result else 0

    list_pipeline = [
        {"$match": query},
        {"$sort": {"statId": 1, "chgerId": 1}},
        {"$group": {
            "_id": "$statId",
            "statNm": {"$first": "$statNm"},
            "addr": {"$first": "$addr"},
            "lat": {"$first": "$lat"},
            "lng": {"$first": "$lng"},
            "busiNm": {"$first": "$busiNm"},
            "chargers": {"$push": {
                "chgerId": "$chgerId",
                "chgerType": "$chgerType",
                "output": "$output",
            }},
        }},
        {"$skip": skip},
        {"$limit": limit},
    ]

    stations = []
    for doc in db.charger_master.aggregate(list_pipeline):
        chargers = []
        available = 0
        for c in doc.get("chargers", []):
            stat = status_map.get((doc["_id"], c["chgerId"]))
            if stat == "2":
                available += 1
            chargers.append(ChargerInfo(
                chgerId=c["chgerId"],
                chgerType=c.get("chgerType"),
                output=c.get("output"),
                stat=stat,
                statLabel=STAT_LABELS.get(stat) if stat else None,
            ))
        stations.append(StationItem(
            statId=doc["_id"],
            statNm=doc.get("statNm"),
            addr=doc.get("addr"),
            lat=doc.get("lat"),
            lng=doc.get("lng"),
            busiNm=doc.get("busiNm"),
            chargers=chargers,
            totalChargers=len(chargers),
            availableChargers=available,
        ))

    return StationListResponse(stations=stations, total=station_total)


def get_districts(db: Database) -> DistrictListResponse:
    latest = db.charger_status_snapshot.find_one(sort=[("collectedAtBucket", -1), ("collectedAt", -1)])
    updated_at = latest["collectedAtKst"] if latest else None
    status_map = _build_status_map(db)

    gu_data: dict[str, dict] = {}
    for doc in db.charger_master.find(
        {"delYn": {"$ne": "Y"}},
        {"statId": 1, "chgerId": 1, "addr": 1, "_id": 0},
    ):
        gu = _extract_gu(doc.get("addr"))
        if not gu:
            continue
        if gu not in gu_data:
            gu_data[gu] = {"stations": set(), "chargers": 0, "available": 0}
        gu_data[gu]["stations"].add(doc["statId"])
        gu_data[gu]["chargers"] += 1
        if status_map.get((doc["statId"], doc["chgerId"])) == "2":
            gu_data[gu]["available"] += 1

    districts = sorted(
        [
            DistrictSummary(
                name=gu,
                stations=len(d["stations"]),
                chargers=d["chargers"],
                available=d["available"],
            )
            for gu, d in gu_data.items()
        ],
        key=lambda x: -x.stations,
    )
    return DistrictListResponse(districts=districts, updatedAt=updated_at)


def get_station_detail(db: Database, stat_id: str) -> StationDetailResponse | None:
    masters = sorted(
        db.charger_master.find(
            {"statId": stat_id, "delYn": {"$ne": "Y"}},
            {"_id": 0, "statId": 1, "chgerId": 1, "statNm": 1, "addr": 1, "lat": 1, "lng": 1,
             "busiNm": 1, "busiCall": 1, "chgerType": 1, "output": 1, "kind": 1, "kindDetail": 1,
             "method": 1, "parkingFree": 1, "limitYn": 1, "limitDetail": 1, "useTime": 1, "raw": 1},
        ),
        key=lambda x: x.get("chgerId", ""),
    )
    if not masters:
        return None

    status_by_charger: dict[str, dict] = {
        doc["chgerId"]: doc
        for doc in db.charger_current.find(
            {"statId": stat_id},
            {"_id": 0, "chgerId": 1, "stat": 1, "statUpdDt": 1, "raw": 1},
        )
        if doc.get("chgerId")
    }

    first = masters[0]
    raw_m = first.get("raw") or {}

    chargers: list[ChargerDetailItem] = []
    for m in masters:
        cid = m.get("chgerId", "")
        status = status_by_charger.get(cid, {})
        raw_s = status.get("raw") or {}
        stat = status.get("stat") or raw_s.get("stat")
        chger_type = m.get("chgerType")

        chargers.append(ChargerDetailItem(
            chgerId=cid,
            chgerType=chger_type,
            chgerTypeLabel=CHGER_TYPE_LABELS.get(str(chger_type)) if chger_type else None,
            output=m.get("output"),
            speedType=_speed_type(chger_type, m.get("output")),
            stat=stat,
            statLabel=STAT_LABELS.get(str(stat)) if stat else None,
            statUpdDt=_format_kst_compact(status.get("statUpdDt") or raw_s.get("statUpdDt")),
            nowTsdt=_format_kst_compact(raw_s.get("nowTsdt")),
            lastTsdt=_format_kst_compact(raw_s.get("lastTsdt")),
            lastTedt=_format_kst_compact(raw_s.get("lastTedt")),
        ))

    kind_code = first.get("kind") or raw_m.get("kind")
    floor_num = raw_m.get("floorNum")
    floor_type = raw_m.get("floorType")
    updated_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    return StationDetailResponse(
        statId=stat_id,
        statNm=first.get("statNm") or raw_m.get("statNm"),
        addr=first.get("addr"),
        useTime=first.get("useTime") or raw_m.get("useTime"),
        busiNm=first.get("busiNm") or raw_m.get("busiNm"),
        busiCall=first.get("busiCall") or raw_m.get("busiCall"),
        parkingFree=first.get("parkingFree") or raw_m.get("parkingFree"),
        limitYn=first.get("limitYn") or raw_m.get("limitYn"),
        limitDetail=first.get("limitDetail") or raw_m.get("limitDetail"),
        kind=kind_code,
        kindLabel=KIND_LABELS.get(str(kind_code)) if kind_code else None,
        kindDetail=first.get("kindDetail") or raw_m.get("kindDetail"),
        method=first.get("method") or raw_m.get("method"),
        maker=raw_m.get("maker"),
        year=raw_m.get("year"),
        floorNum=str(floor_num) if floor_num not in (None, "null", "") else None,
        floorType=str(floor_type) if floor_type not in (None, "null", "") else None,
        lat=first.get("lat"),
        lng=first.get("lng"),
        chargers=chargers,
        updatedAt=updated_at,
    )


def get_stats(db: Database) -> StatsResponse | None:
    latest = db.charger_stats.find_one(
        {"type": "basic_status_snapshot"},
        sort=[("collectedAtBucket", -1)],
    )
    if not latest:
        return None
    return StatsResponse(
        totalChargers=latest.get("totalChargers", 0),
        statusCounts={str(k): v for k, v in latest.get("statusCounts", {}).items()},
        generatedAt=latest.get("generatedAt"),
        generatedAtKst=latest.get("generatedAtKst"),
    )
