import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export interface Project {
  id: number
  name: string
  slug: string
  description: string | null
  doc_count?: number
  updated_at: string
}

export interface Entity {
  id: number
  name: string
  type: string
}

export interface Relation {
  subject: string
  predicate: string
  object: string
}

export interface MetaItem {
  label: string
  value: string
}

export interface WikiDoc {
  id: number
  title: string
  content_md: string
  meta: MetaItem[]
  categories: string[]
  source_type: string
  created_at: string
  updated_at: string
}

export interface Revision {
  id: number
  summary: string
  source_type: string
  occurred_on: string | null
  created_at: string
}

export interface IngestResult {
  document: WikiDoc
  change_summary: string
  project: Project
  entities: Entity[]
  relations: Relation[]
}

export interface Citation {
  document_id: number
  title: string
  occurred_on: string | null
  created_at: string
  project_slug: string
  snippet: string
  score: number
}

export interface SearchResult {
  answer: string
  citations: Citation[]
}

export const projectsApi = {
  list: () => api.get<Project[]>('/projects'),
  create: (name: string, description?: string) =>
    api.post<Project>('/projects', { name, description }),
  get: (slug: string) => api.get<{
    project: Project
    document: WikiDoc | null
    revisions: Revision[]
    entities: Entity[]
    relations: Relation[]
  }>(`/projects/${slug}`),
  editDocument: (slug: string, content_md: string, meta: MetaItem[], name?: string) =>
    api.put<{ ok: boolean; slug: string }>(`/projects/${slug}/document`, { content_md, meta, name }),
  editConversational: (slug: string, message: string) =>
    api.post<IngestResult[]>(`/projects/${slug}/edit`, { message }),
}

export const ingestApi = {
  submit: (payload: { text?: string; project_slug?: string; files?: File[]; urls?: string[] }) => {
    const fd = new FormData()
    if (payload.text) fd.append('text', payload.text)
    if (payload.project_slug) fd.append('project_slug', payload.project_slug)
    for (const f of payload.files ?? []) fd.append('files', f, f.name)
    for (const u of payload.urls ?? []) fd.append('urls', u)
    return api.post<IngestResult[]>('/ingest', fd)
  },
}

export const searchApi = {
  query: (q: string, project_slug?: string) =>
    api.post<SearchResult>('/search', { query: q, project_slug }),
}

export interface ReviewItem {
  id: number
  project_id: number | null
  project_name: string | null
  project_slug: string | null
  kind: string
  context: string | null
  question: string
  created_at: string
}

export const reviewsApi = {
  list: () => api.get<ReviewItem[]>('/reviews'),
  count: () => api.get<{ count: number }>('/reviews/count'),
  resolve: (id: number, answer?: string) => api.post(`/reviews/${id}/resolve`, { answer }),
  dismiss: (id: number) => api.post(`/reviews/${id}/dismiss`),
}

export default api
