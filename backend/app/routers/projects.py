from fastapi import APIRouter, HTTPException
from slugify import slugify

from ..core.db import get_conn
from ..models import (
    ConversationalEditRequest, IngestResult, ManualEditRequest, Project, ProjectCreate, ProjectDetail,
)
from ..services import ingest as ingest_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _proj_out(row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "slug": row["slug"],
        "description": row.get("description"),
        "doc_count": row.get("doc_count"),
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else "",
    }


@router.get("")
def list_projects() -> list[Project]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.*, COUNT(r.id) AS doc_count
               FROM projects p LEFT JOIN revisions r ON r.project_id = p.id
               GROUP BY p.id ORDER BY p.updated_at DESC"""
        ).fetchall()
    return [_proj_out(r) for r in rows]


@router.post("")
def create_project(body: ProjectCreate) -> Project:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "이름이 비어 있습니다.")
    base = slugify(name) or "project"
    with get_conn() as conn:
        slug, i = base, 2
        while conn.execute("SELECT 1 FROM projects WHERE slug = %s", (slug,)).fetchone():
            slug = f"{base}-{i}"; i += 1
        row = conn.execute(
            "INSERT INTO projects (name, slug, description) VALUES (%s, %s, %s) RETURNING *",
            (name, slug, body.description),
        ).fetchone()
        conn.commit()
    return {**_proj_out(row), "doc_count": 0}


@router.get("/{slug}")
def get_project(slug: str) -> ProjectDetail:
    with get_conn() as conn:
        project = conn.execute("SELECT * FROM projects WHERE slug = %s", (slug,)).fetchone()
        if not project:
            raise HTTPException(404, "프로젝트를 찾을 수 없습니다.")
        pid = project["id"]
        doc = conn.execute("SELECT * FROM documents WHERE project_id = %s", (pid,)).fetchone()
        revs = conn.execute(
            """SELECT id, summary, source_type, occurred_on, created_at
               FROM revisions WHERE project_id = %s ORDER BY created_at DESC""",
            (pid,),
        ).fetchall()
        entities = conn.execute(
            "SELECT id, name, type FROM entities WHERE project_id = %s ORDER BY name", (pid,)
        ).fetchall()
        rels = conn.execute(
            """SELECT s.name AS subject, r.predicate, o.name AS object
               FROM relations r
               JOIN entities s ON s.id = r.subject_id
               JOIN entities o ON o.id = r.object_id
               WHERE r.project_id = %s""",
            (pid,),
        ).fetchall()

    return ProjectDetail(
        project=_proj_out({**project, "doc_count": 1 if doc else 0}),
        document=({
            "id": doc["id"], "title": doc["title"], "content_md": doc["content_md"],
            "meta": doc["meta"], "categories": doc["categories"],
            "source_type": doc["source_type"],
            "created_at": doc["created_at"].isoformat(),
            "updated_at": doc["updated_at"].isoformat(),
        } if doc else None),
        revisions=[{
            "id": v["id"], "summary": v["summary"], "source_type": v["source_type"],
            "occurred_on": str(v["occurred_on"]) if v["occurred_on"] else None,
            "created_at": v["created_at"].isoformat(),
        } for v in revs],
        entities=[{"id": e["id"], "name": e["name"], "type": e["type"]} for e in entities],
        relations=[{"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]} for r in rels],
    )


@router.put("/{slug}/document")
def edit_document(slug: str, body: ManualEditRequest):
    """수동 편집 — 본문/메타를 직접 저장. 카테고리·온톨로지·검색 인덱스 재반영."""
    try:
        new_slug = ingest_service.manual_edit(slug, body.content_md, [m.model_dump() for m in body.meta], body.name)
        return {"ok": True, "slug": new_slug}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"수정 실패: {e}")


@router.post("/{slug}/edit")
def edit_conversational(slug: str, body: ConversationalEditRequest) -> list[IngestResult]:
    """대화식 편집 — 지시/추가 내용을 위키에 병합. (해당 프로젝트로 직행, 라우팅 없음)"""
    if not body.message.strip():
        raise HTTPException(400, "내용이 비어 있습니다.")
    try:
        return ingest_service.run_ingest(text=body.message, project_slug=slug)
    except Exception as e:
        raise HTTPException(500, f"수정 실패: {e}")
