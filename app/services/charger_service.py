import re

from pymongo.database import Database

from app.schemas.charger import (
    ChargerInfo,
    DistrictListResponse,
    DistrictSummary,
    StationItem,
    StationListResponse,
    StatsResponse,
)

STAT_LABELS: dict[str, str] = {
    "0": "알수없음",
    "1": "통신이상",
    "2": "사용가능",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "9": "알수없음",
}


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
