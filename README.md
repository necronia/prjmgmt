# PrjMgmt — 자연어 기반 프로젝트 위키

내가 관리하는 프로젝트들의 위키를 **자연어로 입력·관리·검색**하는 웹앱.
자료를 자연어/대량 텍스트/파일로 넣으면 AI가 읽어 **프로젝트당 하나의 위키 문서에 병합**하고, 변경/추가 내용에 수정 날짜를 표기해 항상 최신을 유지하며, 자연어 질문에 **근거 링크와 함께** 답한다.

## 핵심 기능

- **자연어 입력**: 자연어 한 줄, 긴 텍스트 붙여넣기, **파일 첨부**(PDF·PPTX·DOCX·XLSX·이미지·텍스트) → AI가 알아서 읽어 정리
  - 여러 파일을 한 번에 드래그앤드롭, 클립보드 붙여넣기(⌘V), 파일 선택 모두 지원
  - 문서는 로컬 파싱(pypdf/python-pptx/python-docx/openpyxl), 이미지는 Claude vision OCR
- **단일 위키 + 수정 이력**: 프로젝트당 위키 문서 1개를 계속 병합 갱신. 변경/추가 사실엔 `(YYYY-MM-DD 수정)` 표기, 별도 "수정 이력"(날짜+요약) 제공
- **온톨로지 데이터 레이어**: 엔티티/관계를 추출해 그래프 형태로 저장 (관계형 엣지 테이블)
- **하이브리드 검색**: 다국어 임베딩 벡터(코사인) + pg_trgm 키워드 → RRF 융합 → 수정 날짜 맥락 반영 → Claude 답변 합성
- **근거 제공**: 답변과 함께 출처 문서(제목/날짜) 링크

## 아키텍처

```
frontend (React + Vite, AXGENTIC 디자인)  → Caddy :8080
backend  (FastAPI + Anthropic + FastEmbed BGE-M3)  :8000
db       (PostgreSQL 16 + pgvector + pg_trgm)      :5432
```

- LLM: **Claude** (자연어 이해 / 이미지 OCR / 답변 합성)
- 임베딩: **multilingual MiniLM** 로컬 (FastEmbed/ONNX, 384-dim, 한국어 지원, 가볍고 빠름). 품질↑이 필요하면 `multilingual-e5-large`(1024)나 bge-m3로 env+차원만 바꿔 업그레이드. (bge-m3 dense는 fastembed의 TextEmbedding 미지원)
- 저장: **PostgreSQL 단일 컨테이너** — 벡터 + 키워드 + 온톨로지를 한 DB에서

## 실행 (Docker, 한 방)

```bash
cp .env.example .env
# .env 에 ANTHROPIC_API_KEY 입력

docker compose up --build
```

- 웹앱: http://localhost:8080
- API 문서: http://localhost:8000/docs

> 최초 빌드 시 BGE-M3 모델(~2.2GB)을 백엔드 이미지에 prefetch 하므로 시간이 걸린다.

## 로컬 개발

```bash
# DB만 컨테이너로
docker compose up -d db

# 백엔드
cd backend && pip install -r requirements.txt
export DATABASE_URL=postgresql://prjmgmt:prjmgmt@localhost:5432/prjmgmt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload --port 8000

# 프론트 (별 터미널)
cd frontend && npm install && npm run dev   # http://localhost:5173 (/api 는 8000으로 프록시)
```

## 데이터 모델

| 테이블 | 역할 |
|--------|------|
| `projects` | 프로젝트 |
| `documents` | 프로젝트당 1개의 위키 문서 (in-place 갱신, `UNIQUE(project_id)`) |
| `revisions` | 수정 이력 (갱신 1건당 1행: 날짜 + 변경 요약) |
| `chunks` | 검색 단위 (pgvector 임베딩 + trigram 키워드) |
| `entities` | 온톨로지 노드 |
| `relations` | 온톨로지 엣지 (근거 문서 연결) |

## 로드맵 (추후)

- Apache AGE 그래프 엔진 전환 (현재는 관계형 엣지로 동등 기능)
- BGE-M3 sparse/multivector(late-interaction) 검색 (fastembed의 SparseTextEmbedding/LateInteraction 또는 sentence-transformers 경유)
- 인증/멀티유저, 온톨로지 그래프 시각화
