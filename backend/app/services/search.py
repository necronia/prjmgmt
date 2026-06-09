"""하이브리드 검색: pgvector(코사인) + pg_trgm(키워드) RRF 융합 → 버전 맥락 → Claude 답변 합성."""
from ..core.config import settings
from ..core.db import get_conn
from ..models import Citation, SearchRequest, SearchResponse
from . import embed, llm

RRF_K = 60


def _rrf(*rankings: list[int]) -> dict[int, float]:
    """각 ranking은 chunk_id의 순위 리스트. Reciprocal Rank Fusion 점수."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    return scores


def run_search(req: SearchRequest) -> SearchResponse:
    qvec = embed.embed_query(req.query)
    qlit = "[" + ",".join(repr(float(x)) for x in qvec) + "]"  # pgvector 리터럴
    k = settings.top_k
    proj_filter = ""
    params_extra: tuple = ()
    if req.project_slug:
        proj_filter = " AND p.slug = %s"
        params_extra = (req.project_slug,)

    with get_conn() as conn:
        # 1) 벡터 검색
        vec_rows = conn.execute(
            f"""SELECT c.id, c.document_id, c.text, 1 - (c.embedding <=> %s::vector) AS score
                FROM chunks c JOIN projects p ON p.id = c.project_id
                WHERE TRUE {proj_filter}
                ORDER BY c.embedding <=> %s::vector LIMIT %s""",
            (qlit, *params_extra, qlit, k),
        ).fetchall()

        # 2) 키워드 검색 (trigram 유사도)
        kw_rows = conn.execute(
            f"""SELECT c.id, c.document_id, c.text, similarity(c.text, %s) AS score
                FROM chunks c JOIN projects p ON p.id = c.project_id
                WHERE c.text %% %s {proj_filter}
                ORDER BY score DESC LIMIT %s""",
            (req.query, req.query, *params_extra, k),
        ).fetchall()

        if not vec_rows and not kw_rows:
            return SearchResponse(answer="관련 자료를 찾지 못했습니다. 먼저 자료를 추가해 주세요.", citations=[])

        # 3) RRF 융합
        by_id = {r["id"]: r for r in vec_rows}
        by_id.update({r["id"]: r for r in kw_rows})
        fused = _rrf([r["id"] for r in vec_rows], [r["id"] for r in kw_rows])
        top_ids = sorted(fused, key=fused.get, reverse=True)[:k]

        # 4) 문서 메타 (프로젝트당 단일 위키). 본문의 (YYYY-MM-DD 수정) 표기가 버전 맥락 역할.
        doc_ids = list({by_id[cid]["document_id"] for cid in top_ids})
        docs = conn.execute(
            """SELECT d.id, d.title, d.updated_at, d.created_at, p.slug AS project_slug
               FROM documents d JOIN projects p ON p.id = d.project_id
               WHERE d.id = ANY(%s)""",
            (doc_ids,),
        ).fetchall()
        doc_map = {d["id"]: d for d in docs}

        # 5) LLM 근거 컨텍스트 구성
        context_blocks = []
        citations: list[Citation] = []
        for cid in top_ids:
            ch = by_id[cid]
            d = doc_map.get(ch["document_id"])
            if not d:
                continue
            updated = d["updated_at"].date().isoformat()
            context_blocks.append(
                f"[#{d['id']}] 위키: {d['title']} | 최종수정: {updated}\n{ch['text']}"
            )

        # 문서 단위 citation (중복 제거, 점수순)
        seen = set()
        for cid in top_ids:
            ch = by_id[cid]
            d = doc_map.get(ch["document_id"])
            if not d or d["id"] in seen:
                continue
            seen.add(d["id"])
            citations.append(Citation(
                document_id=d["id"], title=d["title"],
                occurred_on=d["updated_at"].date().isoformat(),
                created_at=d["created_at"].isoformat(),
                project_slug=d["project_slug"],
                snippet=ch["text"][:240],
                score=round(fused[cid], 4),
            ))

        answer = llm.synthesize(req.query, "\n\n".join(context_blocks))
        return SearchResponse(answer=answer, citations=citations)
