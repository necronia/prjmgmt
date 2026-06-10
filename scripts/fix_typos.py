"""전 프로젝트의 이름/본문 OCR·오타를 보수적으로 교정한다.

사용(컨테이너 안):  python /app/fix_typos.py [--apply]
  --apply 없으면 dry-run (이름 교정안만 출력). 백업은 호출 전에 scripts/backup.sh.
교정 원칙: 명백히 깨진 글자만 교정. 숫자·날짜·금액·고유명사의 '값'은 보존, 내용 추가/삭제 없음.
"""
import sys
from datetime import date

from slugify import slugify

from app.core.config import settings
from app.core.db import get_conn
from app.services import embed, llm
from app.services.ingest import _chunk, _upsert_entity

apply = "--apply" in sys.argv[1:]
today = date.today().isoformat()

CORRECT_TOOL = {
    "name": "correct_typos",
    "description": "OCR/오타로 깨진 한국어 텍스트를 교정한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "corrected_name": {"type": "string", "description": "교정된 프로젝트 이름. 고유명사 오타도 교정(예: 'SK 까승'→'SK 가스')."},
            "corrected_content": {"type": "string", "description": "교정된 본문(마크다운). 내용 추가/삭제 없이 깨진 글자만 교정."},
        },
        "required": ["corrected_name", "corrected_content"],
    },
}
SYSTEM = (
    "너는 한국어 비즈니스 문서의 OCR/오타를 교정하는 교정자다.\n"
    "1) 명백히 깨지거나 오타인 글자만 자연스러운 한국어로 교정한다 "
    "(예: 주진→추진, 경장력→경쟁력, 멘버사→멤버사, 금여→급여, 지행→진행, 우속→후속, 까승→가스).\n"
    "2) 숫자·날짜·금액의 값은 절대 바꾸지 않는다. 고유명사(회사/제품/사람)는 명백히 깨졌을 때만 올바른 표기로 교정한다.\n"
    "3) 내용을 추가하거나 삭제하지 않는다. 마크다운 구조와 (YYYY-MM-DD 수정) 표기는 유지한다.\n"
    "4) 불확실하면 원문을 그대로 둔다."
)


def correct(name: str, content: str) -> dict:
    resp = llm.client().messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        system=SYSTEM,
        tools=[CORRECT_TOOL],
        tool_choice={"type": "tool", "name": "correct_typos"},
        messages=[{"role": "user", "content": f"프로젝트 이름: {name}\n\n본문:\n{content}"}],
    )
    for b in resp.content:
        if b.type == "tool_use" and b.name == "correct_typos":
            return b.input
    return {"corrected_name": name, "corrected_content": content}


with get_conn() as conn:
    rows = conn.execute(
        "SELECT p.id, p.name, p.slug, d.id AS doc_id, d.content_md FROM projects p JOIN documents d ON d.project_id=p.id ORDER BY p.id"
    ).fetchall()

    for r in rows:
        fixed = correct(r["name"], r["content_md"])
        new_name = (fixed.get("corrected_name") or r["name"]).strip()
        new_content = (fixed.get("corrected_content") or r["content_md"]).strip()
        name_changed = new_name != r["name"]
        content_changed = new_content != r["content_md"]

        flag = "  *이름변경*" if name_changed else ""
        print(f"[{r['id']}] {r['name']}" + (f"  →  {new_name}" if name_changed else "") + flag
              + (f"   (본문 {len(r['content_md'])}→{len(new_content)}자)" if content_changed else "   (변경 없음)"))

        if not apply or (not name_changed and not content_changed):
            continue

        # 이름/슬러그 갱신 (충돌 시 접미사)
        new_slug = r["slug"]
        if name_changed:
            base = slugify(new_name) or r["slug"]
            new_slug, i = base, 2
            while conn.execute("SELECT 1 FROM projects WHERE slug=%s AND id<>%s", (new_slug, r["id"])).fetchone():
                new_slug = f"{base}-{i}"; i += 1
            conn.execute("UPDATE projects SET name=%s, slug=%s, updated_at=now() WHERE id=%s", (new_name, new_slug, r["id"]))

        # 본문 갱신 + 재임베딩 + 온톨로지 재추출
        if content_changed:
            conn.execute("UPDATE documents SET content_md=%s, title=%s, updated_at=now() WHERE id=%s",
                         (new_content, new_name, r["doc_id"]))
            conn.execute("DELETE FROM chunks WHERE document_id=%s", (r["doc_id"],))
            chunks = _chunk(new_content)
            for ch, vec in zip(chunks, embed.embed_passages(chunks)):
                vlit = "[" + ",".join(repr(float(x)) for x in vec) + "]"
                conn.execute("INSERT INTO chunks (document_id, project_id, text, embedding) VALUES (%s,%s,%s,%s::vector)",
                             (r["doc_id"], r["id"], ch, vlit))
            # 온톨로지 재추출 (교정된 내용 기반)
            onto = llm.merge("", new_content, [new_name], today, new_name)
            conn.execute("DELETE FROM relations WHERE project_id=%s", (r["id"],))
            conn.execute("DELETE FROM entities WHERE project_id=%s", (r["id"],))
            for e in onto.get("entities", []):
                _upsert_entity(conn, r["id"], e["name"], e.get("type", "unknown"))
            for rel in onto.get("relations", []):
                s_id = _upsert_entity(conn, r["id"], rel["subject"], "unknown")
                o_id = _upsert_entity(conn, r["id"], rel["object"], "unknown")
                conn.execute("INSERT INTO relations (project_id, subject_id, predicate, object_id, document_id) VALUES (%s,%s,%s,%s,%s)",
                             (r["id"], s_id, rel["predicate"], o_id, r["doc_id"]))
        elif name_changed:
            conn.execute("UPDATE documents SET title=%s WHERE id=%s", (new_name, r["doc_id"]))

    if apply:
        conn.commit()
        print("\n✓ 교정 완료")
    else:
        print("\n[dry-run] 적용하려면 --apply")
