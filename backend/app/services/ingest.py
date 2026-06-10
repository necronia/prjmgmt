"""Ingest 파이프라인: 입력(텍스트/파일) → (파싱·OCR) → 라우팅(프로젝트 분리) → 위키 병합 → 재임베딩 → 수정이력 → 온톨로지.

프로젝트 미지정 시 입력을 회사/클라이언트/건 단위로 '분리'(llm.route)해 각 프로젝트로 라우팅한다.
하나의 입력에 여러 회사가 섞여 있으면 각각 별도 프로젝트로 나뉜다(서로 다른 주제를 한 곳에 안 묶음).
프로젝트당 위키 문서는 1개. 라우팅된 조각은 해당 문서에 병합되며 변경/추가 사실엔 날짜가 표기되고 수정 이력 1건이 남는다.
프로젝트를 명시(project_slug)하면 라우팅 없이 그 프로젝트로 직행한다. 결과는 영향받은 프로젝트별 1개.
"""
from datetime import date

from psycopg.types.json import Json
from slugify import slugify

from ..core.db import get_conn
from ..models import IngestResult
from . import embed, extract_files, llm

# (filename, content_type, data) 튜플
FileInput = tuple[str, str | None, bytes]

# 값 모름을 뜻하는 표현들 → '미상' 으로 정규화 (항목 자체는 유지)
_UNKNOWN_SYNONYMS = {"-", "n/a", "na", "unknown", "<unknown>", "미정", "tbd", "?", "미상"}


def _clean_meta(meta: list | None) -> list:
    """빈 라벨/값 항목만 제거. 값 모름 표현은 '미상' 으로 통일(항목은 유지)."""
    out = []
    for m in meta or []:
        if not isinstance(m, dict):
            continue
        label = (m.get("label") or "").strip()
        value = (m.get("value") or "").strip()
        if not label or not value:
            continue
        if value.lower() in _UNKNOWN_SYNONYMS:
            value = "미상"
        out.append({"label": label, "value": value})
    return out


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
    affected: dict[int, dict] = {}
    with get_conn() as conn:
        known = [r["name"] for r in conn.execute("SELECT name FROM projects ORDER BY updated_at DESC").fetchall()]
        forced = conn.execute("SELECT * FROM projects WHERE slug = %s", (project_slug,)).fetchone() if project_slug else None

        for raw_text, source_type in items:
            # 프로젝트 지정이 없으면 입력을 회사/클라이언트/건 단위로 분리(라우팅)
            if forced:
                segments = [{"project_name": forced["name"], "content": raw_text}]
            else:
                segments = llm.route(raw_text, known, today)

            for seg in segments:
                content = (seg.get("content") or "").strip()
                if not content:
                    continue
                project = forced or _resolve_project(conn, None, seg.get("project_name") or "Untitled")
                change_summary = _merge_segment(conn, project, content, source_type, today)
                known = list({*known, project["name"]})  # 같은 배치 후속 라우팅에 반영
                info = affected.setdefault(project["id"], {"project": project, "changes": []})
                info["changes"].append(change_summary)

        conn.commit()
        return [_build_result(conn, info["project"], info["changes"], today) for info in affected.values()]


def _merge_segment(conn, project: dict, content: str, source_type: str, today: str) -> str:
    """확정된 프로젝트의 단일 위키에 content 를 병합하고 change_summary 반환."""
    pre_doc = conn.execute("SELECT * FROM documents WHERE project_id = %s", (project["id"],)).fetchone()
    merged = llm.merge(
        pre_doc["content_md"] if pre_doc else "", content, [project["name"]], today, project["name"],
        existing_meta=pre_doc["meta"] if pre_doc else None,
    )

    title = project["name"]
    content_md = merged.get("content_md") or content
    meta = _clean_meta(merged.get("meta") or (pre_doc["meta"] if pre_doc else []))
    categories = merged.get("categories") or []
    occurred = (merged.get("occurred_on") or "").strip() or today
    change_summary = (merged.get("change_summary") or "내용 업데이트").strip()

    # 단일 문서 upsert
    if pre_doc:
        doc = conn.execute(
            """UPDATE documents SET content_md = %s, meta = %s, categories = %s, title = %s,
                      source_type = %s, updated_at = now()
               WHERE id = %s RETURNING *""",
            (content_md, Json(meta), Json(categories), title, source_type, pre_doc["id"]),
        ).fetchone()
        conn.execute("DELETE FROM chunks WHERE document_id = %s", (doc["id"],))
    else:
        doc = conn.execute(
            """INSERT INTO documents (project_id, title, content_md, meta, categories, source_type)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (project["id"], title, content_md, Json(meta), Json(categories), source_type),
        ).fetchone()

    reindex_chunks(conn, doc["id"], project["id"], content_md, meta)
    add_revision(conn, project["id"], doc["id"], change_summary, source_type, occurred)
    set_ontology(conn, project["id"], doc["id"], merged.get("entities", []), merged.get("relations", []))

    conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project["id"],))
    return change_summary


def reindex_chunks(conn, doc_id: int, project_id: int, content_md: str, meta: list | None = None) -> None:
    """문서 청크를 재생성해 재임베딩 (검색 반영). 메타(고객사/규모 등)도 검색되도록 포함."""
    conn.execute("DELETE FROM chunks WHERE document_id = %s", (doc_id,))
    meta_line = " · ".join(f"{m.get('label')}: {m.get('value')}" for m in (meta or []) if m.get("value"))
    full = (f"프로젝트 정보 — {meta_line}\n\n{content_md}") if meta_line else content_md
    chunks = _chunk(full)
    for ch, vec in zip(chunks, embed.embed_passages(chunks)):
        vlit = "[" + ",".join(repr(float(x)) for x in vec) + "]"
        conn.execute(
            "INSERT INTO chunks (document_id, project_id, text, embedding) VALUES (%s, %s, %s, %s::vector)",
            (doc_id, project_id, ch, vlit),
        )


def add_revision(conn, project_id: int, doc_id: int, summary: str, source_type: str, occurred: str | None) -> None:
    conn.execute(
        "INSERT INTO revisions (project_id, document_id, summary, source_type, occurred_on) VALUES (%s,%s,%s,%s,%s)",
        (project_id, doc_id, summary, source_type, occurred),
    )


def set_ontology(conn, project_id: int, doc_id: int, entities: list, relations: list, replace: bool = False) -> None:
    """엔티티/관계 반영. replace=True 면 프로젝트의 기존 온톨로지를 지우고 새로 구성(수동 편집용)."""
    if replace:
        conn.execute("DELETE FROM relations WHERE project_id = %s", (project_id,))
        conn.execute("DELETE FROM entities WHERE project_id = %s", (project_id,))
    for e in entities:
        _upsert_entity(conn, project_id, e["name"], e.get("type", "unknown"))
    for r in relations:
        subj = _upsert_entity(conn, project_id, r["subject"], "unknown")
        obj = _upsert_entity(conn, project_id, r["object"], "unknown")
        conn.execute(
            "INSERT INTO relations (project_id, subject_id, predicate, object_id, document_id) VALUES (%s,%s,%s,%s,%s)",
            (project_id, subj, r["predicate"], obj, doc_id),
        )


def _build_result(conn, project: dict, changes: list[str], today: str) -> IngestResult:
    doc = conn.execute("SELECT * FROM documents WHERE project_id = %s", (project["id"],)).fetchone()
    ents = conn.execute(
        "SELECT id, name, type FROM entities WHERE project_id = %s ORDER BY name", (project["id"],)
    ).fetchall()
    rels = conn.execute(
        """SELECT s.name AS subject, r.predicate, o.name AS object
           FROM relations r JOIN entities s ON s.id = r.subject_id JOIN entities o ON o.id = r.object_id
           WHERE r.project_id = %s""",
        (project["id"],),
    ).fetchall()
    return IngestResult(
        document={
            "id": doc["id"], "title": doc["title"], "content_md": doc["content_md"],
            "meta": doc["meta"], "categories": doc["categories"],
            "source_type": doc["source_type"],
            "created_at": doc["created_at"].isoformat(),
            "updated_at": doc["updated_at"].isoformat(),
        },
        change_summary=" / ".join(changes),
        project={
            "id": project["id"], "name": project["name"], "slug": project["slug"],
            "description": project.get("description"),
            "updated_at": (project["updated_at"].isoformat() if project.get("updated_at") else today),
        },
        entities=[{"id": e["id"], "name": e["name"], "type": e["type"]} for e in ents],
        relations=[{"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]} for r in rels],
    )


def manual_edit(slug: str, content_md: str, meta: list) -> None:
    """위키 본문/메타를 사용자가 직접 수정. 카테고리·온톨로지·검색 인덱스를 재반영."""
    today = date.today().isoformat()
    with get_conn() as conn:
        project = conn.execute("SELECT * FROM projects WHERE slug = %s", (slug,)).fetchone()
        if not project:
            raise ValueError("프로젝트를 찾을 수 없습니다.")
        info = llm.analyze(content_md)  # 카테고리 + 온톨로지 재추출 (본문은 사용자 것 유지)
        categories = info.get("categories", [])
        meta = _clean_meta(meta)
        doc = conn.execute("SELECT * FROM documents WHERE project_id = %s", (project["id"],)).fetchone()
        if doc:
            doc = conn.execute(
                """UPDATE documents SET content_md=%s, meta=%s, categories=%s, source_type='edit', updated_at=now()
                   WHERE id=%s RETURNING *""",
                (content_md, Json(meta), Json(categories), doc["id"]),
            ).fetchone()
        else:
            doc = conn.execute(
                """INSERT INTO documents (project_id, title, content_md, meta, categories, source_type)
                   VALUES (%s,%s,%s,%s,%s,'edit') RETURNING *""",
                (project["id"], project["name"], content_md, Json(meta), Json(categories)),
            ).fetchone()
        reindex_chunks(conn, doc["id"], project["id"], content_md, meta)
        set_ontology(conn, project["id"], doc["id"], info.get("entities", []), info.get("relations", []), replace=True)
        add_revision(conn, project["id"], doc["id"], "수동 편집", "edit", today)
        conn.execute("UPDATE projects SET updated_at = now() WHERE id = %s", (project["id"],))
        conn.commit()
