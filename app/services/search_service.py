# =============================================================================
# [검색창 자동완성 및 백엔드 쿼리 매핑 마스터 가이드 명세 (총 24개 필드)]
# =============================================================================
# 
# 사용자가 검색창에 'Key == Value' 형태로 복합 조건을 입력할 때 참조할 규격입니다.
# 
# -----------------------------------------------------------------------------
# ■ A 그룹. 범주형 코드 및 문자열 필드 (매칭 연산자: ==, != 만 허용)
# -----------------------------------------------------------------------------
#   * 프론트엔드: 사용자가 국문 밸류를 선택하면 아래 매핑된 DB 코드로 치환하여 전송합니다.
# 
#   1. 충전기 상태 (DB 필드: stat)
#      - "대기중"     -> "2"
#      - "충전중"     -> "3"
#      - "운영중지"   -> "4"
#      - "고장/점검"  -> "5"
# 
#   2. 운영기관 (DB 필드: busiId 또는 busiNm)
#      - "환경부"     -> "ME"
#      - "한국전력"   -> "KE"
#      - "서울시"     -> "SE"
# 
#   3. 충전기 타입 (DB 필드: chgerType)
#      - "DC차데모"                    -> "01"
#      - "AC완속"                      -> "02"
#      - "DC차데모+AC3상"               -> "03"
#      - "DC콤보"                      -> "04"
#      - "DC차데모+DC콤보"             -> "05"
#      - "급속(DC차데모+AC3상+DC콤보)"  -> "06"
#      - "AC3상"                       -> "07"
#      - "DC콤보(완속)"                -> "08"
#      - "NACS"                        -> "09"
#      - "DC콤보+NACS"                 -> "10"
# 
#   4. 주차료 여부 (DB 필드: parkingFree)
#      - "무료"       -> "Y"
#      - "유료"       -> "N"
# 
#   5. 이용 제한 여부 (DB 필드: limitYn)
#      - "제한있음"   -> "Y"
#      - "제한없음(공공)" -> "N"
# 
#   6. 삭제 여부 (DB 필드: delYn)
#      - "정상운영"   -> "N"
#      - "폐쇄/철거"  -> "Y"
# 
#   7. 충전 방식 (DB 필드: method)
#      - 후보 제안군: ["단독", "동시"]
# 
#   8. 시설 대분류 (DB 필드: kind)
#      - "공공시설"   -> "G0"
#      - "문화시설"   -> "E0"
# 
#   9. 시설 상세구분 (DB 필드: kindDetail)
#      - "주민센터"   -> "G003"
#      - "백화점"     -> "D001"
# 
#  10. 설치 구분 (DB 필드: raw.floorType)
#      - "지상"       -> "F"
#      - "지하"       -> "B"
# 
#  11. 이용 제한 구역 (DB 필드: raw.trafficYn)
#      - "해당(혼잡통행료 부과 등)" -> "Y"
#      - "미해당"     -> "N"
# 
# -----------------------------------------------------------------------------
# ■ B 그룹. 자유 텍스트 및 고유 식별자 필드 (매칭 연산자: ==, != 만 허용)
# -----------------------------------------------------------------------------
#   * 백엔드(Python): '==' 연산자 요청 시에도 몽고디비의 '$regex' 패턴 포함 검색 처리를 권장합니다.
# 
#  12. 충전소명 (DB 필드: statNm)      -> 자유 텍스트 입력 유도 (예: == 낙성대동주민센터)
#  13. 주소 (DB 필드: addr)          -> 자유 텍스트 입력 유도 (예: == 관악구 낙성대로)
#  14. 이용시간 (DB 필드: useTime)     -> 자유 텍스트 입력 유도 (예: == 24시간 이용가능)
#  15. 충전소 ID (DB 필드: statId)     -> 고유 영문+숫자 코드 매칭 (예: == ME174013)
#  16. 충전기 번호 (DB 필드: chgerId)   -> 자동완성 후보 제안 배열: ["01", "02", "03", "04", "05"]
#  17. 시군구 코드 (DB 필드: raw.zscode) -> 행정구역 법정동 코드 매칭 (예: 관악구 == 11620)
#  18. 제조사 (DB 필드: raw.maker)     -> 자동완성 후보 제안 배열: ["시그넷", "채비", "중앙제어"]
# 
# -----------------------------------------------------------------------------
# ■ C 그룹. 수치형 및 타임스탬프 필드 (매칭 연산자: ==, !=, <=, <, >=, > 6종 전체 허용)
# -----------------------------------------------------------------------------
#   * 특징: 크기 및 선후 관계 비교 연산이 가능하며, 백엔드에서 몽고디비 문법($gt, $gte, $lt, $lte)으로 매핑합니다.
# 
#  19. 설치 층수 (DB 필드: raw.floorNum)   -> 숫자 비교 형식 (예: == 1 이면 지상 1층)
#  20. 충전 출력 (DB 필드: output)         -> 자동완성 후보 제안 배열: ["7", "50", "100", "200", "350"] (단위: kW)
#  21. 설치 연도 (DB 필드: raw.year)       -> 연도 대소 비교 (예: >= 2024 이면 최근 신설 기기)
#  22. 상태 변경일 (DB 필드: statUpdDt)     -> 14자리 연속 문자열 비교 (예: >= 20260506180000)
#  23. 최근 충전 종료일 (DB 필드: raw.lastTedt) -> 14자리 연속 문자열 비교 (예: <= 20260506180000)
#  24. 최근 충전 시작일 (DB 필드: raw.lastTsdt) -> 14자리 연속 문자열 비교 (예: >= 20260506170000)
# 
# =============================================================================

import re
from datetime import datetime, timezone
from pymongo.database import Database

from app.schemas.search import (
    ChargerResult,
    Condition,
    OrGroup,
    SearchRequest,
    SearchResponse,
)

# ── 필드 매핑 (가이드 명세 24개 필드) ────────────────────────────────
FIELD_MAP: dict[str, dict] = {
    # ▶ B 그룹 — 자유 텍스트 / 고유 식별자
    "충전소명":     {"field": "statNm",           "type": "like"},
    "충전소ID":     {"field": "statId",            "type": "eq"},
    "충전기ID":     {"field": "chgerId",           "type": "eq"},
    "주소":         {"field": "addr",              "type": "like"},
    "시도코드":     {"field": "zcode",             "type": "eq"},
    "시군구코드":   {"field": "raw.zscode",        "type": "eq"},
    "사업자명":     {"field": "busiNm",            "type": "like"},
    "사업자코드":   {"field": "busiId",            "type": "eq"},
    "제조사":       {"field": "raw.maker",         "type": "like"},
    "이용시간":     {"field": "useTime",           "type": "like"},
    # ▶ A 그룹 — 범주형 코드
    "충전기타입":   {"field": "chgerType",         "type": "in"},
    "충전방식":     {"field": "method",            "type": "in"},
    "충전상태":     {"field": "raw.stat",          "type": "in"},
    "주차무료":     {"field": "parkingFree",       "type": "bool"},
    "이용제한":     {"field": "limitYn",           "type": "bool"},
    "삭제여부":     {"field": "delYn",             "type": "bool"},
    "교통영향":     {"field": "raw.trafficYn",     "type": "bool"},
    "충전소구분":   {"field": "kind",              "type": "in"},
    "시설구분상세": {"field": "raw.kindDetail",    "type": "eq"},
    "설치층구분":   {"field": "raw.floorType",     "type": "bool"},  # F=지상, B=지하
    # ▶ C 그룹 — 수치형
    "출력":         {"field": "output",            "type": "range"},
    "설치년도":     {"field": "raw.year",          "type": "range"},
    "설치층수":     {"field": "raw.floorNum",      "type": "range"},
    # ▶ C 그룹 — 타임스탬프 (14자리 문자열 대소 비교)
    "상태변경일":   {"field": "statUpdDt",         "type": "strdate"},
    "최근충전종료": {"field": "raw.lastTedt",      "type": "strdate"},
    "최근충전시작": {"field": "raw.lastTsdt",      "type": "strdate"},
}

# ── 값 변환 매핑 ──────────────────────────────────────────────────────
CHARGER_TYPE_KR: dict[str, str] = {
    "DC차데모":               "01",
    "AC완속":                 "02",
    "DC차데모+AC3상":         "03",
    "DC콤보":                 "04",
    "DC차데모+DC콤보":        "05",
    "DC차데모+AC3상+DC콤보":  "06",
    "급속(DC차데모+AC3상+DC콤보)": "06",
    "AC3상":                  "07",
    "DC콤보(완속)":           "08",
    "NACS":                   "09",
    "DC콤보+NACS":            "10",
}
CHARGER_TYPE_LABEL: dict[str, str] = {v: k for k, v in CHARGER_TYPE_KR.items()}

STAT_KR: dict[str, str] = {
    "알수없음":  "0",
    "통신이상":  "1",
    "사용가능":  "2",
    "충전대기":  "2",
    "대기중":    "2",   # 가이드 별칭
    "충전중":    "3",
    "운영중지":  "4",
    "점검중":    "5",
    "고장/점검": "5",   # 가이드 별칭
}
STAT_LABEL: dict[str, str] = {
    "0": "알수없음", "1": "통신이상", "2": "사용가능",
    "3": "충전중",   "4": "운영중지", "5": "점검중",
}

BUSI_ID_KR: dict[str, str] = {
    "환경부":     "ME",
    "한국전력":   "KE",
    "한국전력공사": "KE",
    "서울시":     "SE",
}

KIND_KR: dict[str, str] = {
    "공공시설": "G0",
    "문화시설": "E0",
}

FLOOR_TYPE_KR: dict[str, str] = {
    "지상": "F",
    "지하": "B",
}

# bool 필드 한글 → Y/N
BOOL_VALUE_KR: dict[str, str] = {
    "무료": "Y", "유료": "N",
    "제한있음": "Y", "제한없음": "N", "제한없음(공공)": "N",
    "정상운영": "N", "폐쇄/철거": "Y", "철거": "Y",
    "해당": "Y", "미해당": "N",
    "지상": "F", "지하": "B",
}

SEOUL_GU_CODE: dict[str, str] = {
    "종로구": "11110", "중구":    "11140", "용산구":   "11170",
    "성동구": "11200", "광진구":  "11215", "동대문구": "11230",
    "중랑구": "11260", "성북구":  "11290", "강북구":   "11305",
    "도봉구": "11320", "노원구":  "11350", "은평구":   "11380",
    "서대문구": "11410", "마포구": "11440", "양천구":  "11470",
    "강서구": "11500", "구로구":  "11530", "금천구":   "11545",
    "영등포구": "11560", "동작구": "11590", "관악구":  "11620",
    "서초구": "11650", "강남구":  "11680", "송파구":   "11710",
    "강동구": "11740",
}

RANGE_OP_MAP: dict[str, str] = {
    ">=": "$gte", "<=": "$lte", ">": "$gt", "<": "$lt",
    "==": "$eq",  "!=": "$ne",
}

# 문자열로 저장된 숫자 필드 ($expr + $toInt 필요)
STR_NUMERIC_FIELDS = {"output", "raw.year", "raw.floorNum"}
# 14자리 문자열 타임스탬프 필드 (어휘적 대소 비교)
STR_DATE_FIELDS = {"statUpdDt", "raw.lastTedt", "raw.lastTsdt"}

# ── 검색창 쿼리 파서: 필드명 별칭 맵 ──────────────────────────────────
# 영문 MongoDB 필드명 또는 한글 별칭 → FIELD_MAP 한글 키
FIELD_ALIAS_MAP: dict[str, str] = {
    # ▶ 영문 (MongoDB-인접)
    "statNm": "충전소명",     "statId": "충전소ID",      "chgerId": "충전기ID",
    "addr": "주소",           "zcode": "시도코드",       "zscode": "시군구코드",
    "busiNm": "사업자명",     "busiId": "사업자코드",
    "chgerType": "충전기타입","output": "출력",          "method": "충전방식",
    "maker": "제조사",        "year": "설치년도",        "stat": "충전상태",
    "parkingFree": "주차무료","limitYn": "이용제한",     "delYn": "삭제여부",
    "trafficYn": "교통영향",  "kind": "충전소구분",      "useTime": "이용시간",
    "kindDetail": "시설구분상세", "floorType": "설치층구분",
    "floorNum": "설치층수",   "statUpdDt": "상태변경일",
    "lastTedt": "최근충전종료", "lastTsdt": "최근충전시작",
    # ▶ 한글 별칭 (FIELD_MAP 키가 아닌 것)
    "운영기관": "사업자코드", "사업자": "사업자코드",
    "충전출력": "출력",       "충전 출력": "출력",
    "상태": "충전상태",       "충전 상태": "충전상태",
    "충전기 타입": "충전기타입", "충전소 구분": "충전소구분",
    "이용 시간": "이용시간",  "이용 제한": "이용제한",
    "삭제 여부": "삭제여부",  "교통 영향": "교통영향",
    "주차 무료": "주차무료",  "설치 년도": "설치년도",
    "충전 방식": "충전방식",  "시설 구분": "충전소구분",
}

# 파서용 단일 조건식 정규식: "필드 연산자 값" 분해
_COND_RE = re.compile(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$", re.DOTALL)


def _resolve_value(key: str, value: str) -> str:
    """사용자 입력값(한글 포함)을 MongoDB 저장 코드로 변환."""
    meta = FIELD_MAP.get(key, {})
    ftype = meta.get("type", "")

    if ftype == "bool":
        # 한글 → Y/N, 설치층구분(F/B) 포함
        return BOOL_VALUE_KR.get(value, value)

    if key == "충전기타입":
        return CHARGER_TYPE_KR.get(value, value)
    if key == "충전상태":
        return STAT_KR.get(value, value)
    if key == "시군구코드":
        return SEOUL_GU_CODE.get(value, value)
    if key == "사업자코드":
        return BUSI_ID_KR.get(value, value)
    if key == "충전소구분":
        return KIND_KR.get(value, value)
    return value


def _build_single(key: str, op: str, value: str) -> dict:
    """Condition 하나를 MongoDB 쿼리 절로 변환."""
    meta = FIELD_MAP.get(key)
    if not meta:
        raise ValueError(f"지원하지 않는 필드: '{key}'")

    field: str = meta["field"]
    ftype: str = meta["type"]
    resolved = _resolve_value(key, value)

    if ftype == "like":
        pattern = {"$regex": resolved, "$options": "i"}
        if op == "!=":
            return {field: {"$not": pattern}}
        return {field: pattern}

    if ftype in ("bool", "eq", "in"):
        # bool은 이미 _resolve_value에서 Y/N(또는 F/B)로 변환됨
        val = resolved.upper() if (ftype == "bool" and resolved in ("y", "n")) else resolved
        if op == "==":
            return {field: val}
        if op == "!=":
            return {field: {"$ne": val}}
        raise ValueError(f"'{key}' 필드는 == / != 만 사용할 수 있습니다.")

    if ftype == "strdate":
        # 14자리 문자열 타임스탬프 — 어휘적 대소 비교
        mongo_op = RANGE_OP_MAP.get(op)
        if not mongo_op:
            raise ValueError(f"날짜 연산자 오류: '{op}'")
        return {field: {mongo_op: resolved}}

    if ftype == "range":
        mongo_op = RANGE_OP_MAP.get(op)
        if not mongo_op:
            raise ValueError(f"범위 연산자 오류: '{op}'")

        try:
            num = float(resolved)
        except ValueError:
            raise ValueError(f"'{key}' 는 숫자여야 합니다: '{value}'")

        if field in STR_NUMERIC_FIELDS:
            # 문자열 저장 숫자 필드는 빈 문자열/비숫자 값에서 MongoDB 변환 에러가 나지 않도록 $convert 사용
            dollar_field = f"${field}"
            safe_number = {
                "$convert": {
                    "input": {"$ifNull": [dollar_field, "0"]},
                    "to": "double",
                    "onError": 0,
                    "onNull": 0,
                }
            }
            return {"$expr": {mongo_op: [safe_number, num]}}

        return {field: {mongo_op: num}}

    raise ValueError(f"알 수 없는 필드 타입: {ftype}")


def _build_mongo_query(filters: list) -> dict:
    """filters 리스트를 AND-조합 MongoDB 쿼리로 변환."""
    and_clauses: list[dict] = []

    for item in filters:
        if isinstance(item, OrGroup):
            or_clauses = [_build_single(c.key, c.op, c.value) for c in item.or_]
            and_clauses.append({"$or": or_clauses})
        elif isinstance(item, Condition):
            and_clauses.append(_build_single(item.key, item.op, item.value))

    if not and_clauses:
        return {}
    if len(and_clauses) == 1:
        return and_clauses[0]
    return {"$and": and_clauses}


# ══════════════════════════════════════════════════════════════════════
# 복합 문자열 쿼리 파서
# ══════════════════════════════════════════════════════════════════════

def _resolve_field_key(raw_key: str) -> str | None:
    """입력 필드명(한글/영문/별칭)을 FIELD_MAP 한글 키로 정규화. 없으면 None."""
    s = raw_key.strip()
    if s in FIELD_MAP:
        return s
    if s in FIELD_ALIAS_MAP:
        return FIELD_ALIAS_MAP[s]
    # 공백·대소문자 무시 폴백
    s_norm = s.lower().replace(" ", "")
    for src, dst in FIELD_ALIAS_MAP.items():
        if src.lower().replace(" ", "") == s_norm:
            return dst
    for key in FIELD_MAP:
        if key.replace(" ", "") == s_norm:
            return key
    return None


def _parse_single_to_condition(cond_str: str) -> Condition | None:
    """'필드 연산자 값' 단일 조건 문자열 → Condition 객체. 실패 시 None."""
    m = _COND_RE.match(cond_str.strip())
    if not m:
        return None
    raw_key, op, raw_value = m.group(1).strip(), m.group(2), m.group(3).strip()
    key = _resolve_field_key(raw_key)
    if not key:
        return None
    return Condition(key=key, op=op, value=raw_value)


def parse_query_string(query: str) -> dict:
    """
    복합 문자열 쿼리를 MongoDB 쿼리 dict로 변환.

    규칙:
      - AND 가 OR 보다 우선순위 높음 (표준 불리언 논리)
      - 연산자 없는 평문 키워드 → 충전소명 부분 검색
      - 지원하지 않는 필드·연산자 조건은 조용히 건너뜀
      - 파싱 실패 시 {} 반환 (전체 조회 fallback)
      - 한글 값("사용가능", "환경부", "무료" 등) 및 영문 코드 양쪽 허용

    Examples::
        "output >= 50 AND stat == 2"
        → {"$and": [{"$expr": ...}, {"raw.stat": "2"}]}

        "busiId == ME AND output >= 50 OR stat == 사용가능"
        → {"$or": [{"$and": [{...}, {...}]}, {"raw.stat": "2"}]}

        "강남역"
        → {"statNm": {"$regex": "강남역", "$options": "i"}}
    """
    try:
        query = query.strip()
        if not query:
            return {}

        # 연산자 없는 평문 키워드 → 충전소명 부분 검색
        if not _COND_RE.search(query):
            return {"statNm": {"$regex": query, "$options": "i"}}

        # OR 분리 (AND 우선 처리)
        or_parts = [p.strip() for p in re.split(r"\bOR\b", query, flags=re.IGNORECASE) if p.strip()]

        or_clauses: list[dict] = []
        for or_part in or_parts:
            and_parts = [p.strip() for p in re.split(r"\bAND\b", or_part, flags=re.IGNORECASE) if p.strip()]
            and_clauses: list[dict] = []

            for cond_str in and_parts:
                cond = _parse_single_to_condition(cond_str)
                if cond is None:
                    continue
                try:
                    clause = _build_single(cond.key, cond.op, cond.value)
                    if clause:
                        and_clauses.append(clause)
                except ValueError:
                    pass  # 지원하지 않는 연산자 등 → 건너뜀

            if not and_clauses:
                continue
            or_clauses.append(and_clauses[0] if len(and_clauses) == 1 else {"$and": and_clauses})

        if not or_clauses:
            return {}
        return or_clauses[0] if len(or_clauses) == 1 else {"$or": or_clauses}

    except Exception:
        return {}


def _try_parse_to_filter_items(query: str) -> tuple[list, dict]:
    """
    쿼리 문자열을 (Condition 리스트, 복합 MongoDB 절)으로 분리.

    - OR 없는 AND 조건 → Condition 리스트 반환 (at 스냅샷 연동 가능)
    - OR 포함 복합 조건 → 빈 리스트 + parse_query_string() dict 반환
    - 평문 키워드 → 충전소명 Condition 반환
    """
    query = query.strip()
    if not query:
        return [], {}

    # 평문 키워드
    if not _COND_RE.search(query):
        return [Condition(key="충전소명", op="==", value=query)], {}

    # OR 포함 → MongoDB dict 직접 처리 (at 스냅샷 미연동)
    if re.search(r"\bOR\b", query, re.IGNORECASE):
        return [], parse_query_string(query)

    # AND 전용 → Condition 리스트 (at 스냅샷 연동 가능)
    and_parts = [p.strip() for p in re.split(r"\bAND\b", query, flags=re.IGNORECASE) if p.strip()]
    conditions: list[Condition] = []
    for part in and_parts:
        cond = _parse_single_to_condition(part)
        if cond:
            conditions.append(cond)
    return conditions, {}


def _find_target_bucket(db: Database, at: datetime) -> datetime | None:
    """at 이전(이하)의 가장 최근 collectedAtBucket을 반환."""
    # naive datetime은 UTC로 취급
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    doc = db.charger_status_snapshot.find_one(
        {"collectedAtBucket": {"$lte": at}},
        sort=[("collectedAtBucket", -1)],
    )
    return doc["collectedAtBucket"] if doc else None


def _find_latest_bucket(db: Database) -> datetime | None:
    """가장 최근 collectedAtBucket을 반환."""
    doc = db.charger_status_snapshot.find_one(
        {},
        sort=[("collectedAtBucket", -1), ("collectedAt", -1)],
    )
    return doc["collectedAtBucket"] if doc else None


def _build_status_map_at(db: Database, bucket: datetime) -> dict[tuple[str, str], str]:
    """특정 bucket의 {(statId, chgerId): stat} 맵을 반환."""
    cursor = db.charger_status_snapshot.find(
        {"collectedAtBucket": bucket},
        {"statId": 1, "chgerId": 1, "stat": 1, "_id": 0},
    )
    return {(doc["statId"], doc["chgerId"]): doc["stat"] for doc in cursor}


def _extract_stat_conditions(filters: list) -> tuple[list[Condition], list]:
    """최상위 단순 충전상태 조건을 분리. OR 그룹 내부는 분리하지 않음."""
    stat_conds: list[Condition] = []
    remaining = []
    for item in filters:
        if isinstance(item, Condition) and item.key == "충전상태":
            stat_conds.append(item)
        else:
            remaining.append(item)
    return stat_conds, remaining


def _match_stat(stat: str, conditions: list[Condition]) -> bool:
    """stat 코드가 모든 조건을 만족하는지 확인 (AND 결합)."""
    for cond in conditions:
        resolved = _resolve_value("충전상태", cond.value)
        if cond.op == "==" and stat != resolved:
            return False
        if cond.op == "!=" and stat == resolved:
            return False
    return True


def _to_result(doc: dict, status_map: dict[tuple[str, str], str] | None = None) -> ChargerResult:
    raw = doc.get("raw") or {}
    ct = doc.get("chgerType")
    stat_id = doc.get("statId")
    chger_id = doc.get("chgerId")

    if status_map is not None and stat_id and chger_id:
        stat = status_map.get((stat_id, chger_id)) or raw.get("stat")
    else:
        stat = raw.get("stat")

    return ChargerResult(
        statId=stat_id,
        chgerId=chger_id,
        statNm=doc.get("statNm"),
        addr=doc.get("addr"),
        lat=doc.get("lat"),
        lng=doc.get("lng"),
        busiNm=doc.get("busiNm"),
        chgerType=ct,
        chgerTypeLabel=CHARGER_TYPE_LABEL.get(ct) if ct else None,
        output=doc.get("output"),
        method=doc.get("method"),
        parkingFree=doc.get("parkingFree"),
        limitYn=doc.get("limitYn"),
        delYn=doc.get("delYn"),
        useTime=doc.get("useTime"),
        kind=doc.get("kind"),
        zcode=doc.get("zcode"),
        zscode=raw.get("zscode"),
        stat=stat,
        statLabel=STAT_LABEL.get(stat) if stat else None,
    )


def search_chargers(db: Database, req: SearchRequest, debug: bool = False) -> SearchResponse:
    filters = list(req.filters)
    target_bucket: datetime | None = None
    status_map: dict[tuple[str, str], str] | None = None
    complex_clause: dict = {}

    # ── query 문자열 파싱 ────────────────────────────────────────────────
    # AND-전용 조건은 Condition 리스트로 변환하여 최신/기준 스냅샷 상태와 연동
    # OR 포함 복합 표현은 MongoDB dict로 변환 후 마지막에 AND 병합
    if req.query and req.query.strip():
        simple_items, complex_clause = _try_parse_to_filter_items(req.query)
        filters = simple_items + filters

    # ── 충전상태 조건 분리 ───────────────────────────────────────────────
    # charger_master.raw.stat은 기본정보 API 기준이라 최신 상태와 다를 수 있음.
    # 따라서 충전상태 조건은 charger_status_snapshot의 최신 bucket 기준으로 Python에서 필터링.
    stat_conds, filters = _extract_stat_conditions(filters)

    if req.at is not None:
        target_bucket = _find_target_bucket(db, req.at)
    else:
        target_bucket = _find_latest_bucket(db)

    if target_bucket is not None:
        status_map = _build_status_map_at(db, target_bucket)

    # 기준 시각보다 이전 데이터가 없는데 상태 조건이 있으면 결과 없음
    if stat_conds and not status_map:
        return SearchResponse(
            results=[],
            total=0,
            snapshot_bucket=target_bucket,
            query_debug={} if debug else None,
        )

    # ── master 쿼리 빌드 ────────────────────────────────────────────────
    query = _build_mongo_query(filters)

    # OR 포함 복합 절 병합
    # 주의: 복합 OR 내부의 충전상태 조건은 기존 호환성을 위해 MongoDB raw.stat 기준으로 처리됨.
    # 일반 검색창의 '충전상태 == 사용가능 AND 출력 >= 50' 형태는 위 stat_conds 경로로 최신 snapshot과 연동됨.
    if complex_clause:
        query = {"$and": [query, complex_clause]} if query else complex_clause

    # 상태 조건이 있으면 전체 후보를 순회하며 snapshot 상태로 필터링 후 skip/limit 적용
    if stat_conds:
        matched: list[ChargerResult] = []
        total = 0
        cursor = db.charger_master.find(query)
        for doc in cursor:
            stat_id = doc.get("statId")
            chger_id = doc.get("chgerId")
            current_stat = status_map.get((stat_id, chger_id)) if status_map is not None else None
            if not _match_stat(current_stat or "", stat_conds):
                continue
            if total >= req.skip and len(matched) < req.limit:
                matched.append(_to_result(doc, status_map))
            total += 1

        return SearchResponse(
            results=matched,
            total=total,
            snapshot_bucket=target_bucket,
            query_debug=query if debug else None,
        )

    total = db.charger_master.count_documents(query)
    cursor = (
        db.charger_master
        .find(query)
        .skip(req.skip)
        .limit(req.limit)
    )
    results = [_to_result(doc, status_map) for doc in cursor]

    return SearchResponse(
        results=results,
        total=total,
        snapshot_bucket=target_bucket,
        query_debug=query if debug else None,
    )
