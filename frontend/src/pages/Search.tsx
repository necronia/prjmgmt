import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Search as SearchIcon, Loader2, Link2 } from 'lucide-react'
import { searchApi, projectsApi, type SearchResult, type Project } from '../api/client'

export default function Search() {
  const [projects, setProjects] = useState<Project[]>([])
  const [projectSlug, setProjectSlug] = useState('')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { projectsApi.list().then((r) => setProjects(r.data)) }, [])

  const run = async () => {
    if (!q.trim()) return
    setLoading(true); setError(null); setResult(null)
    try {
      const r = await searchApi.query(q.trim(), projectSlug || undefined)
      setResult(r.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '검색 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="panel p-5 mb-5">
        <div className="flex gap-2">
          <select
            className="input w-44 flex-shrink-0"
            value={projectSlug}
            onChange={(e) => setProjectSlug(e.target.value)}
          >
            <option value="">전체 프로젝트</option>
            {projects.map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
          <input
            className="input flex-1"
            placeholder="예) JARVIS의 OpenRouter 폴백은 지금 어떻게 동작해?"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && run()}
          />
          <button className="btn-primary btn-md flex-shrink-0" onClick={run} disabled={loading || !q.trim()}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <SearchIcon size={16} />}
            검색
          </button>
        </div>
      </div>

      {error && <div className="panel p-5 text-sm text-ax-danger">{error}</div>}

      {result && (
        <div className="space-y-4">
          <div className="panel p-6">
            <article className="prose-wiki text-sm text-ax-text leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown>
            </article>
          </div>

          {result.citations.length > 0 && (
            <div className="panel p-5">
              <div className="flex items-center gap-2 section-title mb-3">
                <Link2 size={15} /> 근거 ({result.citations.length})
              </div>
              <div className="space-y-2">
                {result.citations.map((c) => (
                  <Link
                    key={c.document_id}
                    to={`/projects/${c.project_slug}`}
                    className="block panel-flat p-3 hover:bg-ax-subtle transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-ax-text truncate">{c.title}</span>
                      <span className="text-[11px] text-ax-muted flex-shrink-0">
                        {c.occurred_on ?? c.created_at.slice(0, 10)}
                      </span>
                    </div>
                    <p className="text-xs text-ax-muted mt-1 line-clamp-2">{c.snippet}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
