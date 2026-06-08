"""Ingest 파이프라인: 입력(텍스트/파일) → (파싱·OCR) → 구조화 추출 → 버전 문서 → 청크 임베딩 → 온톨로지.

파일 여러 개를 한 번에 넣으면 각 파일이 하나의 위키 문서가 된다. 타이핑한 메모가 있으면
각 파일에 컨텍스트로 덧붙는다(프로젝트 판단·요약에 활용). 파일이 없으면 메모 자체가 한 문서.
"""
from datetime import date

from slugify import slugify

from ..core.db import get_conn
from ..models import IngestResult
from . import embed, extract_files, llm

# (filename, content_type, data) 튜플
FileInput = tuple[str, str | None, bytes]


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


def run_ingest(text: str | None = None, files: list[FileInput] | None = None,
               project_slug: str | None = None) -> list[IngestResult]:
    note = (text or "").strip()
    files = files or []

    # 입력 아이템 구성: (raw_text, source_type)
    items: list[tuple[str, str]] = []
    if files:
        for filename, content_type, data in files:
            extracted, src = extract_files.extract_file(filename, content_type, data)
            if not extracted.strip():
                continue  # 추출 텍스트 없음(예: 스캔 PDF) → 건너뜀
            header = f"[파일: {filename}]"
            prefix = f"[사용자 메모]\n{note}\n\n" if note else ""
            items.append((f"{prefix}{header}\n{extracted}", src))
    elif note:
        items.append((note, "paste" if len(note) > 400 else "nl"))

    if not items:
        raise ValueError("처리할 입력이 없습니다. 텍스트를 쓰거나 읽을 수 있는 파일을 첨부하세요.")

    today = date.today().isoformat()
    results: list[IngestResult] = []
    with get_conn() as conn:
        for raw_text, source_type in items:
            results.append(_ingest_one(conn, raw_text, source_type, project_slug, today))
    return results


def _ingest_one(conn, raw_text: str, source_type: str, project_slug: str | None, today: str) -> IngestResult:
    known = [r["name"] for r in conn.execute("SELECT name FROM projects ORDER BY updated_at DESC").fetchall()]
    hinted = None
    if project_slug:
        p = conn.execute("SELECT name FROM projects WHERE slug = %s", (project_slug,)).fetchone()
        hinted = p["name"] if p else None

    # 2) 구조화 추출
    ex = llm.extract(raw_text, known, today, hinted)

    # 3) 프로젝트 귀속
    project = _resolve_project(conn, project_slug, ex.get("project_name") or "Untitled")

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
    for e in ex.get("entities", []):
        eid = _upsert_entity(conn, project["id"], e["name"], e.get("type", "unknown"))
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
