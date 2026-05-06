from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.db.mongodb import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import search_chargers

router = APIRouter()


@router.post("", response_model=SearchResponse, summary="충전기 조건 검색")
def search(
    req: SearchRequest,
    debug: bool = Query(default=False, description="MongoDB 쿼리 포함 여부"),
    db: Database = Depends(get_db),
):
    """
    한글 키 + 연산자 + 값으로 충전기를 검색합니다.

    **filters** 배열 안에 두 가지 항목을 섞어 쓸 수 있습니다.

    - **단순 조건**: `{"key": "충전상태", "op": "==", "value": "2"}`
    - **OR 그룹**: `{"or": [{"key": "충전상태", "op": "==", "value": "2"}, ...]}`

    filters 항목 간은 AND로 결합됩니다.

    **지원 연산자**: `==` `!=` `>=` `<=` `>` `<`

    **지원 키**:
    충전소명, 충전소ID, 충전기ID, 주소, 시도코드, 시군구코드,
    사업자명, 사업자코드, 충전기타입, 출력, 충전방식, 제조사,
    설치년도, 충전상태, 주차무료, 이용제한, 삭제여부, 교통영향,
    충전소구분, 이용시간
    """
    try:
        return search_chargers(db, req, debug=debug)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
