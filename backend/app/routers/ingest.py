from fastapi import APIRouter, HTTPException

from ..models import IngestRequest, IngestResult
from ..services.ingest import run_ingest

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("")
def ingest(body: IngestRequest) -> IngestResult:
    try:
        return run_ingest(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Ingest 실패: {e}")
