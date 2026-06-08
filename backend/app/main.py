import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import ingest, projects, search
from .services import embed

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("prjmgmt")

app = FastAPI(title="PrjMgmt — Project Wiki API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(ingest.router)
app.include_router(search.router)


@app.on_event("startup")
def _startup():
    # 임베딩 모델 미리 로드 (최초 요청 지연 방지). 실패해도 기동은 계속.
    try:
        log.info("임베딩 모델 로딩…")
        embed.warmup()
        log.info("임베딩 모델 준비 완료")
    except Exception as e:  # noqa: BLE001
        log.warning("임베딩 워밍업 실패(첫 요청 시 재시도): %s", e)


@app.get("/health")
def health():
    return {"status": "ok"}
