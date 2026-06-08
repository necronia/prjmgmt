from fastapi import APIRouter, HTTPException

from ..models import SearchRequest, SearchResponse
from ..services.search import run_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("")
def search(body: SearchRequest) -> SearchResponse:
    if not body.query.strip():
        raise HTTPException(400, "질문이 비어 있습니다.")
    try:
        return run_search(body)
    except Exception as e:
        raise HTTPException(500, f"검색 실패: {e}")
