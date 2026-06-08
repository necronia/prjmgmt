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

export interface DocVersion {
  id: number
  title: string
  content_md: string
  source_type: string
  occurred_on: string | null
  supersedes_id: number | null
  created_at: string
}

export interface IngestResult {
  document: DocVersion
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
    versions: DocVersion[]
    entities: Entity[]
    relations: Relation[]
  }>(`/projects/${slug}`),
}

export const ingestApi = {
  submit: (payload: { text?: string; image_base64?: string; project_slug?: string }) =>
    api.post<IngestResult>('/ingest', payload),
}

export const searchApi = {
  query: (q: string, project_slug?: string) =>
    api.post<SearchResult>('/search', { query: q, project_slug }),
}

export default api
