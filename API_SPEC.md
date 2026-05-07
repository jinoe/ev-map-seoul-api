# EV Map Seoul API 명세서

**Base URL** `http://localhost:400`  
**API Prefix** `/api/v1`  
**Content-Type** `application/json`

---

## 목차
1. [헬스체크](#1-헬스체크)
2. [충전소 목록 조회](#2-충전소-목록-조회)
3. [구별 현황 조회](#3-구별-현황-조회)
4. [전체 통계 조회](#4-전체-통계-조회)
5. [상세 통계 및 분석 (신규)](#5-상세-통계-및-분석-신규)
6. [충전기 조건 검색](#6-충전기-조건-검색)
7. [검색 필드 레퍼런스](#7-검색-필드-레퍼런스)
8. [에러 응답](#8-에러-응답)

---

## 1. 헬스체크
...
---

## 5. 상세 통계 및 분석 (신규)

대시보드 및 사이드바용 상세 통계 데이터를 제공합니다.

### 5.1 지역별 상세 개요 (Overview)

특정 지역(구, 동)의 현재 상태 요약과 통계를 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/stats/overview` |

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `gu` | string | 구 이름 필터 (예: `강남구`) |
| `dong` | string | 동 이름 필터 (예: `역삼동`) |
| `at` | datetime | 기준 시각 (ISO 8601) |

**Response `200 OK`**

```json
{
  "scope": { "gu": "강남구", "dong": null },
  "updatedAt": "2026-05-06T14:30:00+09:00",
  "totalChargers": 612,
  "totalStations": 248,
  "rapidChargers": 120,
  "slowChargers": 480,
  "ultraFastChargers": 12,
  "availableCount": 184,
  "chargingCount": 320,
  "faultCount": 108,
  "maintenanceCount": 20,
  "stoppedCount": 45,
  "communicationErrorCount": 43,
  "unknownCount": 0,
  "availabilityRate": 30.06,
  "avgOutput": 25.5,
  "maxOutput": 350.0,
  "longOccupancy": {
    "count": 5,
    "thresholdMinutes": 360,
    "items": [
      {
        "statId": "ME200001",
        "chgerId": "01",
        "statNm": "강남역 주차장",
        "addr": "...",
        "gu": "강남구",
        "dong": "역삼동",
        "output": "50",
        "nowTsdt": "20240320100000",
        "durationMinutes": 420,
        "lat": 37.4979,
        "lng": 127.0276
      }
    ]
  },
  "statusDistribution": { "사용가능": 184, "충전중": 320, ... },
  "chargerTypeDistribution": { "완속": 480, "급속": 120, "초급속": 12 },
  "facilityDistribution": { "공공시설": 100, "아파트": 400, ... }
}
```

### 5.2 대시보드 분석 데이터 (Dashboard)

대시보드 차트 구현을 위한 시계열 및 집계 데이터를 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/stats/dashboard` |

### 5.3 자치구 리스트 통계

서울시 전체 자치구별 주요 지표 리스트를 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/stats/districts` |

### 5.4 행정동 리스트 통계

특정 자치구 내 행정동별 통계를 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/stats/districts/{gu}/dongs` |

---

## 6. 충전기 조건 검색

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/health` |

### Request

파라미터 없음

### Response `200 OK`

```json
{
  "status": "ok",
  "env": "local",
  "mongodb": "ok"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | 서버 상태 (`ok`) |
| `env` | string | 실행 환경 (`local` \| `server`) |
| `mongodb` | string | MongoDB 연결 상태 (`ok` \| 에러 메시지) |

### 테스트

```bash
curl http://localhost:400/health
```

---

## 2. 충전소 목록 조회

충전소를 페이지네이션으로 조회합니다. 충전기를 충전소 단위로 묶어 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/chargers` |

### Query Parameters

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `limit` | integer | `100` | 반환 최대 건수 (최대 1000) |
| `skip` | integer | `0` | 건너뛸 건수 (페이지네이션) |
| `gu` | string | - | 구 이름 필터 (예: `강남구`) |

### Response `200 OK`

```json
{
  "stations": [
    {
      "statId": "ME2000002",
      "statNm": "강남역 주차장",
      "addr": "서울특별시 강남구 강남대로 396",
      "lat": 37.4979,
      "lng": 127.0276,
      "busiNm": "한국전력공사",
      "chargers": [
        {
          "chgerId": "01",
          "chgerType": "04",
          "output": "50",
          "stat": "2",
          "statLabel": "사용가능"
        },
        {
          "chgerId": "02",
          "chgerType": "02",
          "output": "7",
          "stat": "3",
          "statLabel": "충전중"
        }
      ],
      "totalChargers": 2,
      "availableChargers": 1
    }
  ],
  "total": 13010
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `stations` | array | 충전소 목록 |
| `stations[].statId` | string | 충전소 ID |
| `stations[].statNm` | string | 충전소명 |
| `stations[].addr` | string | 주소 |
| `stations[].lat` | float | 위도 |
| `stations[].lng` | float | 경도 |
| `stations[].busiNm` | string | 운영기관명 |
| `stations[].chargers` | array | 충전기 목록 |
| `stations[].chargers[].chgerId` | string | 충전기 ID |
| `stations[].chargers[].chgerType` | string | 충전기 타입 코드 |
| `stations[].chargers[].output` | string | 충전용량 (kW) |
| `stations[].chargers[].stat` | string | 충전기 상태 코드 |
| `stations[].chargers[].statLabel` | string | 충전기 상태 한글 |
| `stations[].totalChargers` | integer | 총 충전기 수 |
| `stations[].availableChargers` | integer | 사용가능 충전기 수 |
| `total` | integer | 전체 충전소 수 |

### 테스트

```bash
# 기본 조회
curl "http://localhost:400/api/v1/chargers?limit=10"

# 강남구 충전소 조회
curl "http://localhost:400/api/v1/chargers?gu=강남구&limit=20"

# 두 번째 페이지 (101~200번)
curl "http://localhost:400/api/v1/chargers?limit=100&skip=100"
```

---

## 3. 구별 현황 조회

서울시 25개 자치구별 충전소 현황을 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/chargers/districts` |

### Request

파라미터 없음

### Response `200 OK`

```json
{
  "districts": [
    {
      "name": "강남구",
      "stations": 248,
      "chargers": 612,
      "available": 184
    },
    {
      "name": "서초구",
      "stations": 218,
      "chargers": 534,
      "available": 160
    }
  ],
  "updatedAt": "2026-05-06T14:30:00+09:00"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `districts` | array | 구별 현황 목록 (충전소 수 내림차순) |
| `districts[].name` | string | 구 이름 |
| `districts[].stations` | integer | 충전소 수 |
| `districts[].chargers` | integer | 충전기 수 |
| `districts[].available` | integer | 현재 사용가능 충전기 수 |
| `updatedAt` | string | 마지막 상태 수집 시각 (KST ISO 8601) |

### 테스트

```bash
curl http://localhost:400/api/v1/chargers/districts
```

---

## 4. 전체 통계 조회

가장 최근 수집된 전체 충전기 상태 통계를 반환합니다.

| 항목 | 내용 |
|------|------|
| **Method** | `GET` |
| **Endpoint** | `/api/v1/stats` |

### Request

파라미터 없음

### Response `200 OK`

```json
{
  "totalChargers": 73935,
  "statusCounts": {
    "0": 120,
    "1": 340,
    "2": 45210,
    "3": 18900,
    "4": 5200,
    "5": 4165
  },
  "generatedAt": "2026-05-06T05:30:00.000Z",
  "generatedAtKst": "2026-05-06T14:30:00+09:00"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `totalChargers` | integer | 전체 충전기 수 |
| `statusCounts` | object | 상태코드별 충전기 수 |
| `statusCounts["0"]` | integer | 알수없음 |
| `statusCounts["1"]` | integer | 통신이상 |
| `statusCounts["2"]` | integer | 사용가능 |
| `statusCounts["3"]` | integer | 충전중 |
| `statusCounts["4"]` | integer | 운영중지 |
| `statusCounts["5"]` | integer | 점검중 |
| `generatedAt` | string | 통계 생성 시각 (UTC) |
| `generatedAtKst` | string | 통계 생성 시각 (KST) |

### Response `404 Not Found`

통계 데이터가 아직 없는 경우 (pipeline 미실행)

```json
{ "detail": "통계 데이터가 없습니다" }
```

### 테스트

```bash
curl http://localhost:400/api/v1/stats
```

---

## 5. 충전기 조건 검색

한글 키 + 연산자 + 값으로 충전기를 조건 검색합니다.  
`filters` 배열의 항목들은 **AND** 로 결합되며, OR 조건은 `or` 그룹으로 표현합니다.

Method: `POST`  
URL: `/api/v1/search`

---

### 예시 1 — 사용가능 + 주차무료 + 50kW 이상

**Request**

```json
{
  "filters": [
    { "key": "충전상태", "op": "==", "value": "2" },
    { "key": "주차무료", "op": "==", "value": "Y" },
    { "key": "출력",     "op": ">=", "value": "50" }
  ],
  "limit": 100,
  "skip": 0
}
```

**Response**

```json
{
  "results": [
    {
      "statId": "ME2000002",
      "chgerId": "01",
      "statNm": "강남역 주차장",
      "addr": "서울특별시 강남구 강남대로 396",
      "lat": 37.4979,
      "lng": 127.0276,
      "busiNm": "한국전력공사",
      "chgerType": "04",
      "chgerTypeLabel": "DC콤보",
      "output": "50",
      "method": "단독",
      "parkingFree": "Y",
      "limitYn": "N",
      "delYn": "N",
      "useTime": "24시간 이용가능",
      "kind": "F0",
      "zcode": "11",
      "zscode": "11680",
      "stat": "2",
      "statLabel": "사용가능"
    }
  ],
  "total": 1284,
  "query_debug": null
}
```

---

### 예시 2 — 관악구에서 사용가능 또는 충전중 (OR 그룹)

**Request**

```json
{
  "filters": [
    { "key": "시군구코드", "op": "==", "value": "관악구" },
    {
      "or": [
        { "key": "충전상태", "op": "==", "value": "2" },
        { "key": "충전상태", "op": "==", "value": "3" }
      ]
    }
  ],
  "limit": 100,
  "skip": 0
}
```

**Response**

```json
{
  "results": [
    {
      "statId": "PL204001",
      "chgerId": "01",
      "statNm": "관악구청 주차장",
      "addr": "서울특별시 관악구 관악로 145",
      "lat": 37.4783,
      "lng": 126.9516,
      "busiNm": "서울특별시",
      "chgerType": "04",
      "chgerTypeLabel": "DC콤보",
      "output": "50",
      "method": "단독",
      "parkingFree": "N",
      "limitYn": "N",
      "delYn": "N",
      "useTime": "24시간 이용가능",
      "kind": "F0",
      "zcode": "11",
      "zscode": "11620",
      "stat": "2",
      "statLabel": "사용가능"
    }
  ],
  "total": 312,
  "query_debug": null
}
```

---

### 예시 3 — 환경부 운영, DC콤보, 100kW 이상

**Request**

```json
{
  "filters": [
    { "key": "사업자명",   "op": "==", "value": "환경부" },
    { "key": "충전기타입", "op": "==", "value": "DC콤보" },
    { "key": "출력",       "op": ">=", "value": "100" }
  ],
  "limit": 100,
  "skip": 0
}
```

**Response**

```json
{
  "results": [
    {
      "statId": "ME1050001",
      "chgerId": "01",
      "statNm": "한국환경공단 서울지사",
      "addr": "서울특별시 마포구 월드컵북로 396",
      "lat": 37.5765,
      "lng": 126.8876,
      "busiNm": "한국환경공단",
      "chgerType": "04",
      "chgerTypeLabel": "DC콤보",
      "output": "100",
      "method": "단독",
      "parkingFree": "Y",
      "limitYn": "N",
      "delYn": "N",
      "useTime": "24시간 이용가능",
      "kind": "F0",
      "zcode": "11",
      "zscode": "11440",
      "stat": "2",
      "statLabel": "사용가능"
    }
  ],
  "total": 573,
  "query_debug": null
}
```

---

### 예시 4 — 단일 조건 (DC콤보 전체)

**Request**

```json
{
  "filters": [
    { "key": "충전기타입", "op": "==", "value": "DC콤보" }
  ],
  "limit": 100,
  "skip": 0
}
```

**Response**

```json
{
  "results": [
    {
      "statId": "EV001234",
      "chgerId": "01",
      "statNm": "송파구 공영주차장",
      "addr": "서울특별시 송파구 올림픽로 300",
      "lat": 37.5142,
      "lng": 127.1061,
      "busiNm": "송파구청",
      "chgerType": "04",
      "chgerTypeLabel": "DC콤보",
      "output": "50",
      "method": "단독",
      "parkingFree": "N",
      "limitYn": "N",
      "delYn": "N",
      "useTime": "07:00~23:00",
      "kind": "F0",
      "zcode": "11",
      "zscode": "11710",
      "stat": "2",
      "statLabel": "사용가능"
    }
  ],
  "total": 8423,
  "query_debug": null
}
```

---

### 예시 5 — debug 모드 (MongoDB 쿼리 확인)

**Request**

```
POST /api/v1/search?debug=true
```

```json
{
  "filters": [
    { "key": "충전기타입", "op": "==", "value": "DC콤보" },
    { "key": "출력",       "op": ">=", "value": "100" }
  ],
  "limit": 10,
  "skip": 0
}
```

**Response**

```json
{
  "results": [],
  "total": 573,
  "snapshot_bucket": null,
  "query_debug": {
    "$and": [
      { "chgerType": "04" },
      { "$expr": { "$gte": [ { "$toInt": { "$ifNull": ["$output", "0"] } }, 100 ] } }
    ]
  }
}
```

---

### 예시 6 — 특정 시각 기준 충전 상태 조회 (`at`)

`at` 파라미터를 사용하면 해당 시각 직전에 수집된 가장 최근 10분 주기 스냅샷을 기준으로 `충전상태` 를 필터링합니다.

**Request**

```json
{
  "filters": [
    { "key": "시군구코드", "op": "==", "value": "강남구" },
    { "key": "충전상태",   "op": "==", "value": "사용가능" }
  ],
  "at": "2026-05-06T01:07:30",
  "limit": 50,
  "skip": 0
}
```

> `at` 값 `2026-05-06T01:07:30` → 직전 수집 주기 `2026-05-06T01:00:00` 버킷 데이터 사용

**Response**

```json
{
  "results": [
    {
      "statId": "ME2000002",
      "chgerId": "01",
      "statNm": "강남역 주차장",
      "addr": "서울특별시 강남구 강남대로 396",
      "lat": 37.4979,
      "lng": 127.0276,
      "busiNm": "한국전력공사",
      "chgerType": "04",
      "chgerTypeLabel": "DC콤보",
      "output": "50",
      "method": "단독",
      "parkingFree": "Y",
      "limitYn": "N",
      "delYn": "N",
      "useTime": "24시간 이용가능",
      "kind": "F0",
      "zcode": "11",
      "zscode": "11680",
      "stat": "2",
      "statLabel": "사용가능"
    }
  ],
  "total": 218,
  "snapshot_bucket": "2026-05-06T01:00:00Z",
  "query_debug": null
}
```

---

### Request Body 필드

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `filters` | array | ✅ | - | 조건 목록. 항목 간 AND 결합 |
| `filters[].key` | string | ✅ | - | 한글 필드명 ([필드 목록 참고](#6-검색-필드-레퍼런스)) |
| `filters[].op` | string | ✅ | - | 연산자 (`==` `!=` `>=` `<=` `>` `<`) |
| `filters[].value` | string | ✅ | - | 비교 값 (항상 문자열로 전달) |
| `filters[].or` | array | - | - | OR 그룹. 내부 조건들은 OR 결합 |
| `limit` | integer | - | `100` | 최대 반환 건수 (최대 1000) |
| `skip` | integer | - | `0` | 건너뛸 건수 |
| `at` | string | - | `null` | 조회 기준 시각 (ISO 8601). 미입력 시 마스터 정적 데이터 기준 |

> **`at` 동작 방식**  
> - 충전기 상태(`충전상태`)는 10분 단위로 수집됩니다.  
> - `at` 값 이하의 가장 최근 `collectedAtBucket` 을 찾아 해당 버킷의 스냅샷 데이터로 `충전상태` 를 판단합니다.  
> - `at` 미입력 시: `charger_master.raw.stat` 필드 기준 (마스터 수집 시점 값) 사용.  
> - timezone 미포함 시 UTC로 해석합니다. KST 입력 시 `+09:00` 을 명시하세요.  
> - `at` 이전 스냅샷이 없는 경우: `충전상태` 조건이 있으면 빈 결과 반환.

### Query Parameter

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `debug` | boolean | `false` | `true` 시 `query_debug` 에 실제 MongoDB 쿼리 포함 |

### Response 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `results` | array | 검색된 충전기 목록 |
| `results[].statId` | string | 충전소 ID |
| `results[].chgerId` | string | 충전기 ID |
| `results[].statNm` | string | 충전소명 |
| `results[].addr` | string | 주소 |
| `results[].lat` | float | 위도 |
| `results[].lng` | float | 경도 |
| `results[].busiNm` | string | 운영기관명 |
| `results[].chgerType` | string | 충전기 타입 코드 |
| `results[].chgerTypeLabel` | string | 충전기 타입 한글명 |
| `results[].output` | string | 충전용량 kW |
| `results[].method` | string | 충전방식 (단독 / 동시) |
| `results[].parkingFree` | string | 주차무료 (`Y` / `N`) |
| `results[].limitYn` | string | 이용제한 (`Y` / `N`) |
| `results[].delYn` | string | 삭제여부 (`Y` / `N`) |
| `results[].useTime` | string | 이용가능시간 |
| `results[].kind` | string | 충전소 구분 코드 |
| `results[].zcode` | string | 시도 코드 (서울 `11`) |
| `results[].zscode` | string | 시군구 코드 5자리 |
| `results[].stat` | string | 충전기 상태 코드 (`at` 지정 시 해당 버킷 값) |
| `results[].statLabel` | string | 충전기 상태 한글명 |
| `total` | integer | 조건에 맞는 전체 건수 |
| `snapshot_bucket` | string \| null | 실제 사용된 스냅샷 버킷 시각 (UTC). `at` 미입력 시 `null` |
| `query_debug` | object \| null | MongoDB 쿼리 (`?debug=true` 시 노출) |

### Error Response

**422 Unprocessable Entity** — 잘못된 필드명

```json
{ "detail": "지원하지 않는 필드: '이상한필드'" }
```

**422 Unprocessable Entity** — 숫자 필드에 문자 입력

```json
{ "detail": "'출력' 는 숫자여야 합니다: '빠름'" }
```

---

## 6. 검색 필드 레퍼런스

### 지원 필드 및 연산자

| 한글 키 | MongoDB 필드 | 타입 | 지원 연산자 | 비고 |
|---------|-------------|------|------------|------|
| `충전소명` | `statNm` | like | `==` `!=` | 부분 일치 (대소문자 무시) |
| `충전소ID` | `statId` | eq | `==` `!=` | 정확히 일치 |
| `충전기ID` | `chgerId` | eq | `==` `!=` | |
| `주소` | `addr` | like | `==` `!=` | 부분 일치 |
| `시도코드` | `zcode` | eq | `==` `!=` | 서울: `11` |
| `시군구코드` | `raw.zscode` | eq | `==` `!=` | 구 이름 또는 코드 입력 가능 |
| `사업자명` | `busiNm` | like | `==` `!=` | 부분 일치 |
| `사업자코드` | `busiId` | eq | `==` `!=` | |
| `충전기타입` | `chgerType` | in | `==` `!=` | 한글명 또는 코드 입력 가능 |
| `출력` | `output` | range | `==` `!=` `>=` `<=` `>` `<` | 숫자 (kW) |
| `충전방식` | `method` | in | `==` `!=` | |
| `제조사` | `raw.maker` | like | `==` `!=` | 부분 일치 |
| `설치년도` | `raw.year` | range | `==` `!=` `>=` `<=` `>` `<` | 숫자 (예: `2023`) |
| `충전상태` | `raw.stat` | in | `==` `!=` | 한글명 또는 코드 입력 가능 |
| `주차무료` | `parkingFree` | bool | `==` `!=` | `Y` / `N` |
| `이용제한` | `limitYn` | bool | `==` `!=` | `Y` / `N` |
| `삭제여부` | `delYn` | bool | `==` `!=` | `Y` / `N` |
| `교통영향` | `raw.trafficYn` | bool | `==` `!=` | `Y` / `N` |
| `충전소구분` | `kind` | in | `==` `!=` | |
| `이용시간` | `useTime` | like | `==` `!=` | 부분 일치 |

---

### 충전기 타입 코드

| 한글 입력값 | 코드 |
|------------|------|
| `DC차데모` | `01` |
| `AC완속` | `02` |
| `DC차데모+AC3상` | `03` |
| `DC콤보` | `04` |
| `DC차데모+DC콤보` | `05` |
| `DC차데모+AC3상+DC콤보` | `06` |
| `AC3상` | `07` |
| `DC콤보(완속)` | `08` |
| `NACS` | `09` |
| `DC콤보+NACS` | `10` |

> 한글 입력값과 코드 모두 `value`에 사용 가능합니다.

---

### 충전기 상태 코드

| 한글 입력값 | 코드 | 의미 |
|------------|------|------|
| `알수없음` | `0` | 상태 알 수 없음 |
| `통신이상` | `1` | 통신 불량 |
| `사용가능` / `충전대기` | `2` | 충전 가능 상태 |
| `충전중` | `3` | 현재 충전 진행 중 |
| `운영중지` | `4` | 운영 중지 |
| `점검중` | `5` | 점검 진행 중 |

> `at` 미입력 시 `충전상태` 는 `charger_master.raw.stat` (마스터 수집 시점 값) 기준입니다.  
> `at` 입력 시 해당 시각 직전 10분 스냅샷 기준으로 필터링합니다.

---

### 서울 시군구 코드

| 구 이름 | 코드 | 구 이름 | 코드 |
|---------|------|---------|------|
| 종로구 | 11110 | 강서구 | 11500 |
| 중구 | 11140 | 구로구 | 11530 |
| 용산구 | 11170 | 금천구 | 11545 |
| 성동구 | 11200 | 영등포구 | 11560 |
| 광진구 | 11215 | 동작구 | 11590 |
| 동대문구 | 11230 | 관악구 | 11620 |
| 중랑구 | 11260 | 서초구 | 11650 |
| 성북구 | 11290 | 강남구 | 11680 |
| 강북구 | 11305 | 송파구 | 11710 |
| 도봉구 | 11320 | 강동구 | 11740 |
| 노원구 | 11350 | 서대문구 | 11410 |
| 은평구 | 11380 | 마포구 | 11440 |
| 양천구 | 11470 | | |

> 구 이름(`관악구`) 또는 코드(`11620`) 모두 입력 가능합니다.

---

## 7. 에러 응답

### 공통 에러 포맷

```json
{ "detail": "에러 메시지" }
```

### HTTP 상태 코드

| 상태 코드 | 의미 | 발생 상황 |
|-----------|------|----------|
| `200 OK` | 성공 | |
| `404 Not Found` | 데이터 없음 | 통계 데이터 미생성 |
| `422 Unprocessable Entity` | 요청 오류 | 잘못된 필드명, 지원하지 않는 연산자, 숫자 필드에 문자 입력 |
| `503 Service Unavailable` | MongoDB 오류 | DB 연결 실패 |

### 422 예시 — 잘못된 필드명

```bash
curl -X POST http://localhost:400/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"이상한필드","op":"==","value":"2"}]}'
```

```json
{ "detail": "지원하지 않는 필드: '이상한필드'" }
```

### 422 예시 — 숫자 필드에 문자 입력

```bash
curl -X POST http://localhost:400/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"출력","op":">=","value":"빠름"}]}'
```

```json
{ "detail": "'출력' 는 숫자여야 합니다: '빠름'" }
```

---

## 빠른 테스트 스크립트

API 서버 실행 후 아래 명령으로 모든 엔드포인트를 한 번에 확인할 수 있습니다.

```bash
BASE="http://localhost:400"

echo "=== 1. 헬스체크 ==="
curl -s $BASE/health | python3 -m json.tool

echo -e "\n=== 2. 충전소 목록 (limit=2) ==="
curl -s "$BASE/api/v1/chargers?limit=2" | python3 -m json.tool

echo -e "\n=== 3. 구별 현황 ==="
curl -s $BASE/api/v1/chargers/districts | python3 -m json.tool

echo -e "\n=== 4. 전체 통계 ==="
curl -s $BASE/api/v1/stats | python3 -m json.tool

echo -e "\n=== 5-1. 검색: 사용가능 + 주차무료 + 50kW 이상 ==="
curl -s -X POST $BASE/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"충전상태","op":"==","value":"2"},{"key":"주차무료","op":"==","value":"Y"},{"key":"출력","op":">=","value":"50"}],"limit":3}' \
  | python3 -m json.tool

echo -e "\n=== 5-2. 검색: 관악구 + (사용가능 OR 충전중) ==="
curl -s -X POST $BASE/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"시군구코드","op":"==","value":"관악구"},{"or":[{"key":"충전상태","op":"==","value":"2"},{"key":"충전상태","op":"==","value":"3"}]}],"limit":3}' \
  | python3 -m json.tool

echo -e "\n=== 5-3. 검색: DC콤보 + debug 쿼리 확인 ==="
curl -s -X POST "$BASE/api/v1/search?debug=true" \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"충전기타입","op":"==","value":"DC콤보"},{"key":"출력","op":">=","value":"100"}],"limit":2}' \
  | python3 -m json.tool

echo -e "\n=== 5-6. 검색: at 시간 기준 강남구 사용가능 ==="
curl -s -X POST $BASE/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"key":"시군구코드","op":"==","value":"강남구"},{"key":"충전상태","op":"==","value":"사용가능"}],"at":"2026-05-06T01:07:30","limit":3}' \
  | python3 -m json.tool
```
