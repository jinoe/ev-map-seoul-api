import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.mongodb import close_client, get_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    env = settings.APP_ENV
    uri_preview = settings.mongodb_connection_uri.split("@")[-1]
    logger.info("MongoDB 연결 시작: env=%s, host=%s", env, uri_preview)
    get_client()
    yield
    close_client()
    logger.info("MongoDB 연결 종료")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# 임시로 모든 오리진(도메인) 전면 개방
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개별 IP 대신 "*"를 넣으면 모든 접속을 허용합니다.
    allow_credentials=False,  # allow_origins=["*"] 일 때는 파일 보안상 False로 주어야 에러가 안 납니다.
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(request: Request, exc: PyMongoError):
    logger.error("MongoDB 오류: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": f"MongoDB 연결 오류: {exc}"},
    )


@app.get("/health")
def health_check():
    from app.db.mongodb import get_db
    try:
        get_db().command("ping")
        db_status = "ok"
    except Exception as e:
        db_status = str(e)
    return {"status": "ok", "env": settings.APP_ENV, "mongodb": db_status}

