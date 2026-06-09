"""기존에 여러 프로젝트가 섞여 들어간 단일 프로젝트를 회사/클라이언트/건 단위로 분리한다.

사용(컨테이너 안):  python /app/split_project.py <slug> [--apply]
  --apply 없으면 dry-run (분리 계획만 출력, DB 변경 없음).
백업은 호출 전에 scripts/backup.sh 로 떠둘 것.
"""
import sys
from datetime import date

from app.core.db import get_conn
from app.services import embed, llm
from app.services.ingest import _chunk, _resolve_project, _upsert_entity

slug = sys.argv[1]
apply = "--apply" in sys.argv[2:]
today = date.today().isoformat()

with get_conn() as conn:
    src = conn.execute(
        "SELECT p.*, d.content_md FROM projects p JOIN documents d ON d.project_id = p.id WHERE p.slug = %s",
        (slug,),
    ).fetchone()
    if not src:
        print(f"프로젝트 없음: {slug}"); sys.exit(1)

    known = [r["name"] for r in conn.execute("SELECT name FROM projects").fetchall()]
    segments = llm.route(src["content_md"], known, today, max_tokens=16000)

    # 같은 프로젝트로 분류된 조각은 '병합'(이어붙임) — 덮어쓰기로 인한 유실 방지
    groups: dict[str, str] = {}
    for s in segments:
        name = (s.get("project_name") or "Untitled").strip()
        body = (s.get("content") or "").strip()
        if not body:
            continue
        groups[name] = (groups[name] + "\n\n" + body) if name in groups else body

    print(f"\n=== '{src['name']}' → {len(groups)}개 프로젝트로 분리 계획 ===")
    for name, body in groups.items():
        print(f"  • {name}  ({len(body)}자)")

    if not apply:
        print("\n[dry-run] 적용하려면 --apply 를 붙여 다시 실행.")
        sys.exit(0)

    src_pid = src["id"]
    # 원본의 폴루션 데이터 정리 (문서는 segment 로 재구성)
    for t in ("relations", "entities", "chunks", "revisions"):
        conn.execute(f"DELETE FROM {t} WHERE project_id = %s", (src_pid,))

    touched: set[int] = set()
    for name, body in groups.items():
        project = _resolve_project(conn, None, name)
        touched.add(project["id"])

        # 온톨로지 추출 (본문은 segment 내용을 그대로 사용)
        onto = llm.merge("", body, [name], today, name)

        existing = conn.execute("SELECT * FROM documents WHERE project_id = %s", (project["id"],)).fetchone()
        if existing:
            doc = conn.execute(
                "UPDATE documents SET content_md=%s, title=%s, updated_at=now() WHERE id=%s RETURNING *",
                (body, project["name"], existing["id"]),
            ).fetchone()
            conn.execute("DELETE FROM chunks WHERE document_id = %s", (doc["id"],))
        else:
            doc = conn.execute(
                "INSERT INTO documents (project_id, title, content_md, source_type) VALUES (%s,%s,%s,'paste') RETURNING *",
                (project["id"], project["name"], body),
            ).fetchone()

        chunks = _chunk(body)
        for ch, vec in zip(chunks, embed.embed_passages(chunks)):
            vlit = "[" + ",".join(repr(float(x)) for x in vec) + "]"
            conn.execute(
                "INSERT INTO chunks (document_id, project_id, text, embedding) VALUES (%s,%s,%s,%s::vector)",
                (doc["id"], project["id"], ch, vlit),
            )
        for e in onto.get("entities", []):
            _upsert_entity(conn, project["id"], e["name"], e.get("type", "unknown"))
        for r in onto.get("relations", []):
            s_id = _upsert_entity(conn, project["id"], r["subject"], "unknown")
            o_id = _upsert_entity(conn, project["id"], r["object"], "unknown")
            conn.execute(
                "INSERT INTO relations (project_id, subject_id, predicate, object_id, document_id) VALUES (%s,%s,%s,%s,%s)",
                (project["id"], s_id, r["predicate"], o_id, doc["id"]),
            )
        conn.execute(
            "INSERT INTO revisions (project_id, document_id, summary, source_type, occurred_on) VALUES (%s,%s,%s,'paste',%s)",
            (project["id"], doc["id"], f"'{src['name']}' 통합 문서에서 분리·정리", today),
        )
        conn.execute("UPDATE projects SET updated_at=now() WHERE id=%s", (project["id"],))
        print(f"  -> {project['name']}: chunks {len(chunks)}, entities {len(onto.get('entities', []))}")

    # 원본이 어떤 segment 로도 재사용되지 않았으면(완전히 다른 회사들로만 분리) 빈 원본 제거
    if src_pid not in touched:
        conn.execute("DELETE FROM documents WHERE project_id = %s", (src_pid,))
        conn.execute("DELETE FROM projects WHERE id = %s", (src_pid,))
        print(f"원본 '{src['name']}' 는 분리 후 비어 삭제됨")

    conn.commit()
    print("\n✓ 분리 완료")
