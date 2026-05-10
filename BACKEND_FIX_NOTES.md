# EV Map Seoul API 백엔드 수정 요약

## 수정 대상

- `app/services/stats_service.py`
- `app/services/search_service.py`
- `app/services/charger_service.py`
- `app/main.py`

## 핵심 수정 사항

### 1. `/api/v1/stats/overview` validation error 수정

기존 코드에서 `StatsOverviewResponse`가 요구하는 필드는 `stoppedCount`인데, 실제 반환 코드가 `stopped_count`로 되어 있어 Pydantic validation error가 발생했습니다.

수정 후에는 `stoppedCount=stopped_count` 형태로 정상 반환됩니다.

### 2. 기준 시각 `at` 처리 오류 수정

기존에는 MongoDB datetime 필드에 `at.isoformat()` 문자열을 비교했습니다.

```python
query["collectedAt"] = {"$lte": at.isoformat()}
```

수정 후에는 MongoDB datetime과 datetime을 직접 비교하고, `collectedAtBucket` 기준으로 최신 스냅샷을 찾습니다.

### 3. 상태 스냅샷 join 방식 개선

기존 `/stats/overview`는 MongoDB aggregation `$lookup`과 `$toDouble`에 의존했습니다. `output` 값이 비어 있거나 숫자가 아닌 경우 aggregation error가 날 수 있었습니다.

수정 후에는 다음 방식으로 처리합니다.

1. 기준 bucket 조회
2. 해당 bucket의 `charger_status_snapshot`을 `(statId, chgerId)` map으로 구성
3. `charger_master`와 메모리에서 결합
4. 통계 계산

데이터 규모가 서울시 충전기 수준이면 API 응답 안정성을 우선한 방식입니다.

### 4. 장기 점유 계산 수정

기존 코드는 `statusDoc.nowTsdt`를 읽었지만, 수집기 구조상 실제 값은 대체로 `statusDoc.raw.nowTsdt` 안에 있습니다.

수정 후에는 다음 순서로 읽습니다.

1. `statusDoc.nowTsdt`
2. `statusDoc.raw.nowTsdt`

또한 `nowTsdt`는 KST 문자열이므로, 비교 기준도 KST로 통일했습니다.

### 5. `/api/v1/stats/districts/{gu}/dongs` 구현

기존에는 항상 빈 배열을 반환했습니다.

```python
return []
```

수정 후에는 특정 구의 충전기를 동 단위로 그룹화하여 다음 값을 반환합니다.

- 충전소 수
- 충전기 수
- 사용가능 수
- 충전중 수
- 고장/점검 수
- 가용률
- 평균 출력
- 완속/급속/초급속 수

### 6. `/api/v1/stats/districts` 안정화

기존 Mongo aggregation은 주소 split 위치에 의존해 구 이름을 뽑았습니다.

수정 후에는 `extract_gu()` 함수로 주소 내 `~구` 토큰을 찾아 그룹화합니다.

### 7. `/api/v1/stats/dashboard` 더미 데이터 제거

기존 제조사별 고장률, 설치년도별 고장률, 요일별 가용률은 하드코딩 값이었습니다.

수정 후에는 현재 MongoDB 데이터 기반으로 계산합니다.

- KPI
- 제조사/사업자별 고장률
- 설치년도별 고장률
- 시설 유형 분포
- 자치구 랭킹
- 최근 7일 기준 요일별 가용률
- 최근 7일 기준 시간대 히트맵
- 최근 `charger_stats` 기반 고장 추이

단, 지역 필터 `gu`, `dong`이 들어온 경우에는 snapshot 이력 전체를 지역별로 다시 join하는 비용이 커서 이력성 차트는 빈 배열로 둡니다. 현재 시점 통계는 정상 반환됩니다.

### 8. 검색 API의 충전상태 필터 수정

기존 검색 API는 `충전상태` 조건을 `charger_master.raw.stat`에 의존할 수 있었습니다. 이 값은 최신 상태 스냅샷과 다를 수 있습니다.

수정 후 일반적인 조건 검색은 최신 또는 `at` 기준 snapshot 상태를 사용합니다.

예:

```text
충전상태 == 사용가능 AND 출력 >= 50
```

### 9. 숫자 문자열 비교 안정화

기존 검색 API는 문자열 숫자 필드를 `$toInt`로 변환했습니다. 빈 문자열이나 소수점이 섞이면 MongoDB error가 날 수 있습니다.

수정 후에는 `$convert` + `onError: 0`을 사용합니다.

### 10. 충전소 목록/자치구 목록 API 보정

- 삭제된 충전기 `delYn == Y` 제외
- 구 이름 regex escape 처리
- 최신 bucket 정렬 기준을 `collectedAtBucket`, `collectedAt` 순으로 변경
- 상태 코드 `2` 라벨을 `충전대기`에서 `사용가능`으로 통일

### 11. CORS 설정 정리

기존에는 코드에서 모든 origin을 강제 허용했습니다.

수정 후에는 `.env`의 `ALLOWED_ORIGINS`를 따릅니다.
기본값이 `['*']`이면 기존처럼 전체 허용됩니다.

## 서버 적용 방법

서버에서 기존 백엔드 폴더를 백업한 뒤, 이 수정본으로 교체합니다.

```bash
cd ~
cp -r ev-map-seoul-api ev-map-seoul-api.backup.$(date +%Y%m%d_%H%M%S)
```

수정 파일만 반영한 뒤 문법 확인:

```bash
cd ~/ev-map-seoul-api
python -m compileall app
```

Docker로 운영 중이면 재빌드/재실행:

```bash
docker stop backend-container || true
docker rm backend-container || true

docker build -t ev-backend .
docker run -d \
  --network host \
  --name backend-container \
  --restart always \
  ev-backend
```

상태 확인:

```bash
curl http://127.0.0.1:400/health
curl http://127.0.0.1:400/api/v1/stats/overview
curl http://127.0.0.1:400/api/v1/stats/districts
curl http://127.0.0.1:400/api/v1/stats/districts/강남구/dongs
```
