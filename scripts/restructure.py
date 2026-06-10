"""기존 위키(줄글)를 구조화 포맷으로 재정리한다: 메타(상단) + 카테고리별·시간순 진행내용.

사용(컨테이너 안):  python /app/restructure.py [--apply]
  --apply 없으면 dry-run. 백업은 호출 전에 scripts/backup.sh.
재정리 시 본문 재임베딩 + 카테고리 + 온톨로지(교체)까지 반영.
"""
import sys
from datetime import date

from psycopg.types.json import Json

from app.core.db import get_conn
from app.services import llm
from app.services.ingest import add_revision, reindex_chunks, set_ontology

apply = "--apply" in sys.argv[1:]
today = date.today().isoformat()

with get_conn() as conn:
    rows = conn.execute(
        "SELECT p.id, p.name, d.id AS doc_id, d.content_md FROM projects p JOIN documents d ON d.project_id=p.id ORDER BY p.id"
    ).fetchall()

    for r in rows:
        # 기존 본문을 '새 입력'으로 넣어 구조화본을 생성 (기존 구조 없음)
        s = llm.merge("", r["content_md"], [r["name"]], today, r["name"])
        meta = s.get("meta") or []
        categories = s.get("categories") or []
        content_md = s.get("content_md") or r["content_md"]

        print(f"[{r['id']}] {r['name']}: meta {len(meta)}개, 카테고리 {categories}")

        if not apply:
            continue

        conn.execute(
            "UPDATE documents SET content_md=%s, meta=%s, categories=%s, updated_at=now() WHERE id=%s",
            (content_md, Json(meta), Json(categories), r["doc_id"]),
        )
        reindex_chunks(conn, r["doc_id"], r["id"], content_md, meta)
        set_ontology(conn, r["id"], r["doc_id"], s.get("entities", []), s.get("relations", []), replace=True)
        add_revision(conn, r["id"], r["doc_id"], "구조화 정리 (메타/카테고리/시간순)", "edit", today)
        conn.execute("UPDATE projects SET updated_at=now() WHERE id=%s", (r["id"],))

    if apply:
        conn.commit()
        print("\n✓ 구조화 완료")
    else:
        print("\n[dry-run] 적용하려면 --apply")
