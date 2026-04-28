from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_chargers():
    return {"message": "충전소 목록 API - 구현 예정"}
