from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class SearchRequest(BaseModel):
    query: str
    project_slug: str | None = None


# ── Responses ─────────────────────────────────────────
class Project(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    doc_count: int | None = None
    updated_at: str


class Entity(BaseModel):
    id: int
    name: str
    type: str


class Relation(BaseModel):
    subject: str
    predicate: str
    object: str


class DocVersion(BaseModel):
    id: int
    title: str
    content_md: str
    source_type: str
    occurred_on: str | None = None
    supersedes_id: int | None = None
    created_at: str


class IngestResult(BaseModel):
    document: DocVersion
    project: Project
    entities: list[Entity]
    relations: list[Relation]


class ProjectDetail(BaseModel):
    project: Project
    versions: list[DocVersion]
    entities: list[Entity]
    relations: list[Relation]


class Citation(BaseModel):
    document_id: int
    title: str
    occurred_on: str | None = None
    created_at: str
    project_slug: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    answer: str
    citations: list[Citation]
