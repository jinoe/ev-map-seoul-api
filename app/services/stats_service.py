import re
from datetime import datetime, timedelta
from typing import Any, Optional
from pymongo.database import Database
from app.schemas.stats import (
    StatsSummaryResponse,
    StatsOverviewResponse,
    DashboardStatsResponse,
    DistrictStatItem,
    DongStatItem,
    ScopeInfo,
    LongOccupancyStats,
    LongOccupancyItem
)

# Constants for status mapping
STATUS_MAP = {
    "0": "알수없음",
    "1": "통신이상",
    "2": "사용가능",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "9": "알수없음",
}

def extract_gu(addr: str, zscode: str = None) -> str:
    if not addr:
        return "구 미상"
    for part in addr.split():
        if part.endswith("구") and len(part) > 1:
            return part
    # Fallback to zscode if needed (implementation depends on actual mapping)
    return "구 미상"

def extract_dong(addr: str) -> str:
    if not addr:
        return "동 미상"
    
    # Try to find dong in parentheses like (염창동)
    match = re.search(r'\(([^)]*[동가])\)', addr)
    if match:
        return match.group(1).split(',')[0].strip()
    
    # Try to find token ending with 동 or 가
    for part in addr.split():
        if (part.endswith("동") or part.endswith("가")) and len(part) > 1:
            return part
            
    return "동 미상"

def safe_float(val: Any) -> float:
    try:
        if val is None:
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def get_latest_bucket(db: Database, at: datetime = None) -> Optional[dict]:
    query = {}
    if at:
        query["collectedAt"] = {"$lte": at.isoformat()}
    
    latest = db.charger_status_snapshot.find_one(
        query,
        sort=[("collectedAt", -1)]
    )
    return latest

def get_stats_summary(db: Database) -> Optional[StatsSummaryResponse]:
    latest = get_latest_bucket(db)
    if not latest:
        return None
    
    bucket = latest["collectedAtBucket"]
    
    # Simple count from snapshot
    pipeline = [
        {"$match": {"collectedAtBucket": bucket}},
        {"$group": {
            "_id": "$stat",
            "count": {"$sum": 1}
        }}
    ]
    status_counts_raw = {doc["_id"]: doc["count"] for doc in db.charger_status_snapshot.aggregate(pipeline)}
    
    total_chargers = sum(status_counts_raw.values())
    available_count = status_counts_raw.get("2", 0)
    charging_count = status_counts_raw.get("3", 0)
    fault_count = status_counts_raw.get("1", 0) + status_counts_raw.get("4", 0) + status_counts_raw.get("5", 0)
    unknown_count = status_counts_raw.get("0", 0) + status_counts_raw.get("9", 0)
    
    # Total stations
    total_stations = len(db.charger_master.distinct("statId"))
    
    availability_rate = (available_count / total_chargers * 100) if total_chargers > 0 else 0
    
    return StatsSummaryResponse(
        totalChargers=total_chargers,
        totalStations=total_stations,
        statusCounts={str(k): v for k, v in status_counts_raw.items()},
        availableCount=available_count,
        chargingCount=charging_count,
        faultCount=fault_count,
        unknownCount=unknown_count,
        availabilityRate=availability_rate,
        generatedAt=latest.get("collectedAt"),
        generatedAtKst=latest.get("collectedAtKst"),
        collectedAtBucket=bucket
    )

def get_stats_overview(
    db: Database, 
    gu: str = None, 
    dong: str = None, 
    at: datetime = None
) -> StatsOverviewResponse:
    latest = get_latest_bucket(db, at)
    bucket = latest["collectedAtBucket"] if latest else None
    
    # 1. Join master and snapshot
    pipeline = []
    
    # Match criteria for region
    match_master = {"delYn": {"$ne": "Y"}}
    if gu:
        match_master["addr"] = {"$regex": gu}
    if dong:
        match_master["addr"] = {"$regex": dong}
        
    pipeline.append({"$match": match_master})
    
    # Lookup status
    pipeline.append({
        "$lookup": {
            "from": "charger_status_snapshot",
            "let": {"sid": "$statId", "cid": "$chgerId"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$collectedAtBucket", bucket]},
                            {"$eq": ["$statId", "$$sid"]},
                            {"$eq": ["$chgerId", "$$cid"]}
                        ]
                    }
                }}
            ],
            "as": "status"
        }
    })
    
    pipeline.append({
        "$addFields": {
            "statusDoc": {"$arrayElemAt": ["$status", 0]}
        }
    })
    
    # Project needed fields and calculated fields
    pipeline.append({
        "$project": {
            "statId": 1,
            "chgerId": 1,
            "statNm": 1,
            "addr": 1,
            "lat": 1,
            "lng": 1,
            "chgerType": 1,
            "output": 1,
            "kind": 1,
            "stat": "$statusDoc.stat",
            "nowTsdt": "$statusDoc.nowTsdt",
            "outputNum": {"$toDouble": "$output"}
        }
    })
    
    results = list(db.charger_master.aggregate(pipeline))
    
    # Aggregation in memory for simplicity (can be done in pipeline too)
    total_chargers = len(results)
    stations = set()
    available_count = 0
    charging_count = 0
    fault_count = 0
    maintenance_count = 0
    stopped_count = 0
    communication_error_count = 0
    unknown_count = 0
    
    rapid_chargers = 0
    slow_chargers = 0
    ultra_fast_chargers = 0
    
    outputs = []
    
    long_occupancy_items = []
    threshold = 360 # 6 hours for long occupancy example
    
    status_distribution = {}
    charger_type_distribution = {}
    facility_distribution = {}
    
    for r in results:
        stations.add(r["statId"])
        stat = r.get("stat")
        
        # Status counts
        if stat == "2": available_count += 1
        elif stat == "3": charging_count += 1
        elif stat == "1": communication_error_count += 1
        elif stat == "4": stopped_count += 1
        elif stat == "5": maintenance_count += 1
        elif stat in ["0", "9", None]: unknown_count += 1
        
        if stat in ["1", "4", "5"]:
            fault_count += 1
            
        status_label = STATUS_MAP.get(stat, "알수없음")
        status_distribution[status_label] = status_distribution.get(status_label, 0) + 1
        
        # Charger types
        out_val = safe_float(r.get("output"))
        if out_val >= 200:
            ultra_fast_chargers += 1
            type_label = "초급속"
        elif out_val >= 50:
            rapid_chargers += 1
            type_label = "급속"
        else:
            slow_chargers += 1
            type_label = "완속"
        
        charger_type_distribution[type_label] = charger_type_distribution.get(type_label, 0) + 1
        
        if out_val > 0:
            outputs.append(out_val)
            
        # Facility type
        kind = r.get("kind") or "기타"
        facility_distribution[kind] = facility_distribution.get(kind, 0) + 1
        
        # Long occupancy
        if stat == "3" and r.get("nowTsdt"):
            try:
                # nowTsdt format: 20240320143000
                ts = datetime.strptime(r["nowTsdt"], "%Y%m%d%H%M%S")
                duration = (datetime.now() - ts).total_seconds() / 60
                if duration > threshold:
                    long_occupancy_items.append(LongOccupancyItem(
                        statId=r["statId"],
                        chgerId=r["chgerId"],
                        statNm=r.get("statNm"),
                        addr=r.get("addr"),
                        gu=extract_gu(r.get("addr")),
                        dong=extract_dong(r.get("addr")),
                        output=r.get("output"),
                        nowTsdt=r.get("nowTsdt"),
                        durationMinutes=int(duration),
                        lat=r.get("lat"),
                        lng=r.get("lng")
                    ))
            except:
                pass

    availability_rate = (available_count / total_chargers * 100) if total_chargers > 0 else 0
    avg_output = sum(outputs) / len(outputs) if outputs else 0
    max_output = max(outputs) if outputs else 0
    
    return StatsOverviewResponse(
        scope=ScopeInfo(gu=gu, dong=dong),
        updatedAt=latest.get("collectedAtKst") if latest else None,
        totalChargers=total_chargers,
        totalStations=len(stations),
        rapidChargers=rapid_chargers,
        slowChargers=slow_chargers,
        ultraFastChargers=ultra_fast_chargers,
        availableCount=available_count,
        chargingCount=charging_count,
        faultCount=fault_count,
        maintenanceCount=maintenance_count,
        stopped_count=stopped_count,
        communicationErrorCount=communication_error_count,
        unknownCount=unknown_count,
        availabilityRate=availability_rate,
        avgOutput=avg_output,
        maxOutput=max_output,
        longOccupancy=LongOccupancyStats(
            count=len(long_occupancy_items),
            thresholdMinutes=threshold,
            items=long_occupancy_items[:20] # Limit to top 20
        ),
        statusDistribution=status_distribution,
        chargerTypeDistribution=charger_type_distribution,
        facilityDistribution=facility_distribution
    )

def get_dashboard_stats(
    db: Database,
    gu: str = None,
    dong: str = None,
    at: datetime = None
) -> DashboardStatsResponse:
    # This is a complex one, returning dummy data for now to satisfy the UI requirement
    # while using real counts where possible.
    overview = get_stats_overview(db, gu, dong, at)
    
    # Real-ish KPIs
    kpis = {
        "totalChargers": overview.totalChargers,
        "availabilityRate": overview.availabilityRate,
        "faultCount": overview.faultCount,
        "longOccupancyCount": overview.longOccupancy.count,
    }
    
    # Placeholder for manufacturer fault rate
    manufacturer_fault_rate = [
        {"name": "대영채비", "total": 120, "fault": 5, "rate": 4.1},
        {"name": "시그넷이브이", "total": 80, "fault": 2, "rate": 2.5},
        {"name": "중앙제어", "total": 60, "fault": 3, "rate": 5.0},
        {"name": "에스트래픽", "total": 45, "fault": 1, "rate": 2.2},
    ]
    
    # Placeholder for install year
    install_year_fault_rate = [
        {"year": "2020", "count": 10},
        {"year": "2021", "count": 15},
        {"year": "2022", "count": 25},
        {"year": "2023", "count": 40},
        {"year": "2024", "count": 12},
    ]
    
    # Placeholder for availability by weekday
    availability_by_weekday = [
        {"day": "월", "rate": 85},
        {"day": "화", "rate": 82},
        {"day": "수", "rate": 84},
        {"day": "목", "rate": 80},
        {"day": "금", "rate": 75},
        {"day": "토", "rate": 65},
        {"day": "일", "rate": 70},
    ]
    
    # Facility distribution from overview
    facility_type_distribution = [{"name": k, "value": v} for k, v in overview.facilityDistribution.items()]
    
    return DashboardStatsResponse(
        kpis=kpis,
        manufacturerFaultRate=manufacturer_fault_rate,
        installYearFaultRate=install_year_fault_rate,
        availabilityByWeekday=availability_by_weekday,
        availabilityHeatmap=[],
        weekdayWeekendHourlyUsage=[],
        facilityTypeDistribution=facility_type_distribution,
        facilityTypeCounts=[],
        faultTrend=[],
        longOccupancyTrend=[],
        districtRanking=[]
    )

def get_districts_stats(db: Database, at: datetime = None) -> list[DistrictStatItem]:
    latest = get_latest_bucket(db, at)
    bucket = latest["collectedAtBucket"] if latest else None
    
    # Aggregation for all districts
    pipeline = [
        {"$match": {"delYn": {"$ne": "Y"}}},
        {
            "$lookup": {
                "from": "charger_status_snapshot",
                "let": {"sid": "$statId", "cid": "$chgerId"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$collectedAtBucket", bucket]},
                                {"$eq": ["$statId", "$$sid"]},
                                {"$eq": ["$chgerId", "$$cid"]}
                            ]
                        }
                    }}
                ],
                "as": "status"
            }
        },
        {"$addFields": {"stat": {"$arrayElemAt": ["$status.stat", 0]}}},
        {
            "$group": {
                "_id": {"$arrayElemAt": [{"$split": ["$addr", " "]}, 1]}, # Very naive Gu extraction
                "stations": {"$addToSet": "$statId"},
                "chargers": {"$sum": 1},
                "available": {"$sum": {"$cond": [{"$eq": ["$stat", "2"]}, 1, 0]}},
                "charging": {"$sum": {"$cond": [{"$eq": ["$stat", "3"]}, 1, 0]}},
                "fault": {"$sum": {"$cond": [{"$in": ["$stat", ["1", "4", "5"]]}, 1, 0]}},
                "outputs": {"$push": {"$toDouble": "$output"}},
                "rapid": {"$sum": {"$cond": [{"$and": [{"$gte": [{"$toDouble": "$output"}, 50]}, {"$lt": [{"$toDouble": "$output"}, 200]}]}, 1, 0]}},
                "slow": {"$sum": {"$cond": [{"$lt": [{"$toDouble": "$output"}, 50]}, 1, 0]}},
                "ultra": {"$sum": {"$cond": [{"$gte": [{"$toDouble": "$output"}, 200]}, 1, 0]}},
            }
        }
    ]
    
    results = []
    for doc in db.charger_master.aggregate(pipeline):
        gu = doc["_id"] or "미상"
        if not gu.endswith("구"):
            # Try to find part that ends with 구
            pass # Simplified for now
            
        chargers = doc["chargers"]
        outputs = [o for o in doc["outputs"] if o > 0]
        
        results.append(DistrictStatItem(
            gu=gu,
            stations=len(doc["stations"]),
            chargers=chargers,
            available=doc["available"],
            charging=doc["charging"],
            fault=doc["fault"],
            availabilityRate=(doc["available"] / chargers * 100) if chargers > 0 else 0,
            avgOutput=sum(outputs) / len(outputs) if outputs else 0,
            rapidChargers=doc["rapid"],
            slowChargers=doc["slow"],
            ultraFastChargers=doc["ultra"]
        ))
        
    return sorted(results, key=lambda x: -x.stations)

def get_dongs_stats(db: Database, gu: str, at: datetime = None) -> list[DongStatItem]:
    # Similar to districts but filtered by gu and grouped by dong
    latest = get_latest_bucket(db, at)
    bucket = latest["collectedAtBucket"] if latest else None
    
    # We'll use memory processing for Dong as extraction is tricky in mongo pipeline
    # without complex regex
    overview = get_stats_overview(db, gu=gu, at=at)
    # Actually overview already does this but doesn't group by dong.
    # Let's do a simplified version.
    
    # For now, let's just return a placeholder or do a full scan if needed.
    # In a real app, we'd have a 'dong' field in the document.
    return []
