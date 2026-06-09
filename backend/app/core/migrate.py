"""기동 시 idempotent 스키마 마이그레이션 — 기존 데이터를 보존하며 스키마만 맞춘다.

원칙: 절대 DROP TABLE/볼륨 삭제를 하지 않는다. 테이블/컬럼/인덱스는 '있으면 통과, 없으면 추가'.
새 볼륨이든 기존 볼륨이든 안전하게 현재 스키마로 수렴한다. (db/init.sql 과 동일 스키마)
"""
import logging

from .config import settings
from .db import get_conn

log = logging.getLogger("prjmgmt.migrate")

# 테이블/인덱스 — 모두 IF NOT EXISTS (기존 데이터 영향 없음)
DDL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",

    """CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",

    """CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        content_md TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'nl',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    # 기존(구 스키마) documents 에 빠진 컬럼이 있으면 추가 — 데이터 유지
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
    "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)",

    """CREATE TABLE IF NOT EXISTS revisions (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        summary TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'nl',
        occurred_on DATE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_revisions_project ON revisions(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_revisions_document ON revisions(document_id)",

    f"""CREATE TABLE IF NOT EXISTS chunks (
        id SERIAL PRIMARY KEY,
        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        embedding vector({settings.embed_dim}),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_text_trgm ON chunks USING gin (text gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id)",

    """CREATE TABLE IF NOT EXISTS entities (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'unknown',
        canonical_name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (project_id, canonical_name)
    )""",

    """CREATE TABLE IF NOT EXISTS relations (
        id SERIAL PRIMARY KEY,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        subject_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        predicate TEXT NOT NULL,
        object_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
        document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_relations_project ON relations(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_relations_subject ON relations(subject_id)",
    "CREATE INDEX IF NOT EXISTS idx_relations_object ON relations(object_id)",
]

# 제약(이미 있으면 통과, 없을 때만 추가). 중복 데이터가 있으면 실패해도 기동은 계속.
GUARDED_CONSTRAINTS = [
    ("documents_project_id_key",
     "ALTER TABLE documents ADD CONSTRAINT documents_project_id_key UNIQUE (project_id)"),
]


def run() -> None:
    with get_conn() as conn:
        for stmt in DDL:
            conn.execute(stmt)
        for name, add_sql in GUARDED_CONSTRAINTS:
            exists = conn.execute(
                "SELECT 1 FROM pg_constraint WHERE conname = %s", (name,)
            ).fetchone()
            if not exists:
                try:
                    conn.execute(add_sql)
                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    log.warning("제약 %s 추가 보류(수동 정리 필요): %s", name, e)
        conn.commit()

        # 임베딩 차원 불일치 감지 (데이터는 건드리지 않고 경고만)
        row = conn.execute(
            "SELECT atttypmod FROM pg_attribute WHERE attrelid='chunks'::regclass AND attname='embedding'"
        ).fetchone()
        if row and row["atttypmod"] and row["atttypmod"] != settings.embed_dim:
            log.warning(
                "임베딩 차원 불일치: DB=%s, config=%s. 모델을 바꿨다면 청크 재임베딩이 필요합니다.",
                row["atttypmod"], settings.embed_dim,
            )
    log.info("스키마 마이그레이션 완료 (데이터 보존)")
