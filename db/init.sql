-- PrjMgmt 스키마: pgvector(임베딩) + pg_trgm(키워드) + 관계형 온톨로지
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── 프로젝트 ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── 문서(버전형 위키 엔트리, append-only) ────────────
CREATE TABLE IF NOT EXISTS documents (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    content_md    TEXT NOT NULL,
    source_type   TEXT NOT NULL DEFAULT 'nl',   -- nl | paste | image
    occurred_on   DATE,                          -- 내용상 사건 날짜
    supersedes_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_supersedes ON documents(supersedes_id);

-- ── 청크(검색 단위) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    id          SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    embedding   vector(384),   -- embed_dim 과 일치해야 함 (config.py)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 벡터(코사인) + 키워드(trigram) 하이브리드 인덱스
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_text_trgm ON chunks USING gin (text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);

-- ── 온톨로지: 엔티티(노드) ───────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id             SERIAL PRIMARY KEY,
    project_id     INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    type           TEXT NOT NULL DEFAULT 'unknown',
    canonical_name TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, canonical_name)
);

-- ── 온톨로지: 관계(엣지, 근거 문서 연결) ─────────────
CREATE TABLE IF NOT EXISTS relations (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    subject_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    predicate   TEXT NOT NULL,
    object_id   INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_relations_project ON relations(project_id);
CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject_id);
CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object_id);
