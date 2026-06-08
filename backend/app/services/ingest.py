"""Ingest 파이프라인: 입력 → (OCR) → 구조화 추출 → 버전 문서 저장 → 청크 임베딩 → 온톨로지 upsert."""
from datetime import date

from slugify import slugify

from ..core.db import get_conn
from ..models import IngestRequest, IngestResult
from . import embed, llm


def _chunk(text: str, size: int = 800) -> list[str]:
    """문단 경계 기준 ~size자 청크."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 > size and buf:
            chunks.append(buf)
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf:
        chunks.append(buf)
    return chunks or [text.strip()]


def _resolve_project(conn, project_slug: str | None, project_name: str) -> dict:
    cur = conn.execute
    if project_slug:
        row = cur("SELECT * FROM projects WHERE slug = %s", (project_slug,)).fetchone()
        if row:
            return row
    # 이름으로 매칭 (대소문자 무시)
    row = cur("SELECT * FROM projects WHERE lower(name) = lower(%s)", (project_name,)).fetchone()
    if row:
        return row
    # 신규 생성 (slug 충돌 시 -2, -3 …)
    base = slugify(project_name) or "project"
    slug = base
    i = 2
    while cur("SELECT 1 FROM projects WHERE slug = %s", (slug,)).fetchone():
        slug = f"{base}-{i}"
        i += 1
    return cur(
        "INSERT INTO projects (name, slug) VALUES (%s, %s) RETURNING *",
        (project_name, slug),
    ).fetchone()


def _upsert_entity(conn, project_id: int, name: str, etype: str) -> int:
    canonical = name.strip().lower()
    row = conn.execute(
        """INSERT INTO entities (project_id, name, type, canonical_name)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (project_id, canonical_name)
           DO UPDATE SET name = EXCLUDED.name
           RETURNING id""",
        (project_id, name.strip(), etype, canonical),
    ).fetchone()
    return row["id"]


def run_ingest(req: IngestRequest) -> IngestResult:
    # 1) 입력 텍스트 구성 (이미지면 OCR)
    parts: list[str] = []
    source_type = "nl"
    if req.image_base64:
        parts.append(llm.ocr_image(req.image_base64))
        source_type = "image"
    if req.text and req.text.strip():
        parts.append(req.text.strip())
        if source_type != "image":
            source_type = "paste" if len(req.text) > 400 else "nl"
    raw_text = "\n\n".join(p for p in parts if p)
    if not raw_text.strip():
        raise ValueError("입력 내용이 비어 있습니다.")

    today = date.today().isoformat()

    with get_conn() as conn:
        known = [r["name"] for r in conn.execute("SELECT name FROM projects ORDER BY updated_at DESC").fetchall()]
        hinted = None
        if req.project_slug:
            p = conn.execute("SELECT name FROM projects WHERE slug = %s", (req.project_slug,)).fetchone()
            hinted = p["name"] if p else None

        # 2) 구조화 추출
        ex = llm.extract(raw_text, known, today, hinted)

        # 3) 프로젝트 귀속
        project = _resolve_project(conn, req.project_slug, ex.get("project_name") or "Untitled")

        # 4) 버전 문서 — 같은 제목의 최신 문서를 supersedes
        title = (ex.get("title") or "Untitled").strip()
        prev = conn.execute(
            """SELECT id FROM documents
               WHERE project_id = %s AND lower(title) = lower(%s)
               ORDER BY created_at DESC LIMIT 1""",
            (project["id"], title),
        ).fetchone()
        occurred = (ex.get("occurred_on") or "").strip() or None
        content_md = ex.get("summary_md") or raw_text

        doc = conn.execute(
            """INSERT INTO documents (project_id, title, content_md, source_type, occurred_on, supersedes_id)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (project["id"], title, content_md, source_type, occurred, prev["id"] if prev else None),
        ).fetchone()

        # 5) 청크 임베딩 저장
        chunks = _chunk(content_md)
        vectors = embed.embed_passages(chunks)
        for ch, vec in zip(chunks, vectors):
            vlit = "[" + ",".join(repr(float(x)) for x in vec) + "]"
            conn.execute(
                "INSERT INTO chunks (document_id, project_id, text, embedding) VALUES (%s, %s, %s, %s::vector)",
                (doc["id"], project["id"], ch, vlit),
            )

        # 6) 온톨로지 upsert
        ent_rows = []
        name_to_id: dict[str, int] = {}
        for e in ex.get("entities", []):
            eid = _upsert_entity(conn, project["id"], e["name"], e.get("type", "unknown"))
            name_to_id[e["name"].strip().lower()] = eid
            ent_rows.append({"id": eid, "name": e["name"].strip(), "type": e.get("type", "unknown")})

        rel_rows = []
        for r in ex.get("relations", []):
            subj = _upsert_entity(conn, project["id"], r["subject"], "unknown")
            obj = _upsert_entity(conn, project["id"], r["object"], "unknown")
            conn.execute(
                """INSERT INTO relations (project_id, subject_id, predicate, object_id, document_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (project["id"], subj, r["predicate"], obj, doc["id"]),
            )
            rel_rows.append({"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]})

        # 7) 프로젝트 updated_at 갱신
        conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project["id"],))
        conn.commit()

    return IngestResult(
        document={
            "id": doc["id"], "title": doc["title"], "content_md": doc["content_md"],
            "source_type": doc["source_type"],
            "occurred_on": str(doc["occurred_on"]) if doc["occurred_on"] else None,
            "supersedes_id": doc["supersedes_id"],
            "created_at": doc["created_at"].isoformat(),
        },
        project={
            "id": project["id"], "name": project["name"], "slug": project["slug"],
            "description": project.get("description"),
            "updated_at": (project["updated_at"].isoformat() if project.get("updated_at") else today),
        },
        entities=ent_rows,
        relations=rel_rows,
    )
