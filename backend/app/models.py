from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class SearchRequest(BaseModel):
    query: str
    project_slug: str | None = None


class MetaItem(BaseModel):
    label: str
    value: str


class ManualEditRequest(BaseModel):
    content_md: str
    meta: list[MetaItem] = []
    name: str | None = None


class ConversationalEditRequest(BaseModel):
    message: str


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


class WikiDoc(BaseModel):
    id: int
    title: str
    content_md: str
    meta: list[MetaItem] = []
    categories: list[str] = []
    source_type: str
    created_at: str
    updated_at: str


class Revision(BaseModel):
    id: int
    summary: str
    source_type: str
    occurred_on: str | None = None
    created_at: str


class IngestResult(BaseModel):
    document: WikiDoc
    change_summary: str
    project: Project
    entities: list[Entity]
    relations: list[Relation]


class ProjectDetail(BaseModel):
    project: Project
    document: WikiDoc | None = None
    revisions: list[Revision]
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


class ReviewItem(BaseModel):
    id: int
    project_id: int | None = None
    project_name: str | None = None
    project_slug: str | None = None
    kind: str
    context: str | None = None
    question: str
    created_at: str


class ResolveReviewRequest(BaseModel):
    answer: str | None = None
