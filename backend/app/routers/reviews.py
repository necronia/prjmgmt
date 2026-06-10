from fastapi import APIRouter, HTTPException

from ..core.db import get_conn
from ..models import ResolveReviewRequest, ReviewItem
from ..services import ingest as ingest_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("")
def list_reviews() -> list[ReviewItem]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.id, r.project_id, r.kind, r.context, r.question, r.created_at,
                      p.name AS project_name, p.slug AS project_slug
               FROM review_items r LEFT JOIN projects p ON p.id = r.project_id
               WHERE r.status = 'open' ORDER BY r.created_at DESC"""
        ).fetchall()
    return [{
        "id": r["id"], "project_id": r["project_id"],
        "project_name": r["project_name"], "project_slug": r["project_slug"],
        "kind": r["kind"], "context": r["context"], "question": r["question"],
        "created_at": r["created_at"].isoformat(),
    } for r in rows]


@router.get("/count")
def review_count():
    with get_conn() as conn:
        row = conn.execute("SELECT count(*) AS n FROM review_items WHERE status='open'").fetchone()
    return {"count": row["n"]}


@router.post("/{item_id}/resolve")
def resolve_review(item_id: int, body: ResolveReviewRequest):
    with get_conn() as conn:
        item = conn.execute("SELECT * FROM review_items WHERE id=%s", (item_id,)).fetchone()
        if not item:
            raise HTTPException(404, "항목을 찾을 수 없습니다.")
        slug = None
        if item["project_id"]:
            p = conn.execute("SELECT slug FROM projects WHERE id=%s", (item["project_id"],)).fetchone()
            slug = p["slug"] if p else None
        conn.execute("UPDATE review_items SET status='resolved', resolved_at=now() WHERE id=%s", (item_id,))
        conn.commit()

    # 답변이 있으면 해당 프로젝트 위키에 반영(대화식 편집)
    answer = (body.answer or "").strip()
    if answer and slug:
        msg = f"확인 요청에 대한 답변: {item['question']}\n→ {answer}"
        try:
            ingest_service.run_ingest(text=msg, project_slug=slug)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"항목은 처리됐으나 위키 반영 실패: {e}")
    return {"ok": True}


@router.post("/{item_id}/dismiss")
def dismiss_review(item_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE review_items SET status='dismissed', resolved_at=now() WHERE id=%s", (item_id,))
        conn.commit()
    return {"ok": True}
