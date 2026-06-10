"""기존 위키에서 OCR 깨짐/불확실 항목을 찾아 '확인 필요' 함에 적재한다.

사용(컨테이너 안):  python /app/scan_reviews.py
"""
from app.core.db import get_conn
from app.services import llm
from app.services.ingest import add_clarifications

with get_conn() as conn:
    rows = conn.execute(
        "SELECT p.id, p.name, d.id AS doc_id, d.content_md FROM projects p JOIN documents d ON d.project_id=p.id ORDER BY p.id"
    ).fetchall()
    total = 0
    for r in rows:
        info = llm.analyze(r["content_md"])
        clars = info.get("clarifications", []) or []
        add_clarifications(conn, r["id"], r["doc_id"], clars)
        if clars:
            total += len(clars)
            print(f"[{r['id']}] {r['name']}: +{len(clars)}")
            for c in clars:
                print(f"    - {c.get('question')}")
    conn.commit()
    print(f"\n✓ 확인 필요 항목 {total}건 적재")
