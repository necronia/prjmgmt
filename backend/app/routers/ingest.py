from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..models import IngestResult
from ..services.ingest import run_ingest

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("")
async def ingest(
    text: str | None = Form(None),
    project_slug: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
) -> list[IngestResult]:
    file_inputs = []
    for f in files:
        data = await f.read()
        if data:
            file_inputs.append((f.filename or "file", f.content_type, data))
    try:
        return run_ingest(text=text, files=file_inputs, project_slug=project_slug)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Ingest 실패: {e}")
