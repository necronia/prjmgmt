import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Loader2, History, Network, FileText, Plus } from 'lucide-react'
import { format } from 'date-fns'
import { projectsApi, type DocVersion, type Entity, type Relation, type Project } from '../api/client'

export default function ProjectWiki() {
  const { slug } = useParams<{ slug: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [versions, setVersions] = useState<DocVersion[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [relations, setRelations] = useState<Relation[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => {
    if (!slug) return
    setLoading(true)
    projectsApi.get(slug)
      .then((r) => {
        setProject(r.data.project)
        setVersions(r.data.versions)
        setEntities(r.data.entities)
        setRelations(r.data.relations)
        setSelected(r.data.versions[0]?.id ?? null)
      })
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-ax-muted gap-2">
      <Loader2 size={18} className="animate-spin" /> 불러오는 중…
    </div>
  }
  if (!project) return <div className="p-6 text-ax-muted">프로젝트를 찾을 수 없습니다.</div>

  const current = versions.find((v) => v.id === selected) ?? versions[0]

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="page-header">
        <div>
          <h2 className="page-title">{project.name}</h2>
          {project.description && <p className="section-subtitle">{project.description}</p>}
        </div>
        <Link to={`/ingest?project=${project.slug}`} className="btn-primary btn-md">
          <Plus size={16} /> 자료 추가
        </Link>
      </div>

      {versions.length === 0 ? (
        <div className="panel p-10 text-center text-ax-muted">
          <FileText size={32} className="mx-auto mb-3 opacity-40" />
          아직 자료가 없습니다. <Link to={`/ingest?project=${project.slug}`} className="text-ax-accent">자료 추가</Link>로 시작하세요.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
          {/* 현재 위키 본문 */}
          <div className="panel p-6 min-w-0">
            {current && (
              <>
                <div className="flex items-center gap-2 mb-4 flex-wrap">
                  <span className="badge-blue">{current.source_type}</span>
                  {current.id === versions[0].id && <span className="badge-green">최신</span>}
                  <span className="text-xs text-ax-muted">
                    {current.occurred_on ?? format(new Date(current.created_at), 'yyyy-MM-dd')}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-ax-text mb-3">{current.title}</h3>
                <article className="prose-wiki text-sm text-ax-text leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {current.content_md}
                  </ReactMarkdown>
                </article>
              </>
            )}
          </div>

          {/* 사이드: 타임라인 + 온톨로지 */}
          <div className="space-y-4 min-w-0">
            <div className="panel p-4">
              <div className="flex items-center gap-2 section-title mb-3">
                <History size={15} /> 버전 타임라인
              </div>
              <div className="space-y-1">
                {versions.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => setSelected(v.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      v.id === selected ? 'bg-ax-subtle text-ax-text font-medium border border-ax-border' : 'text-ax-muted hover:bg-ax-subtle'
                    }`}
                  >
                    <div className="truncate">{v.title}</div>
                    <div className="text-[11px] text-ax-muted">
                      {v.occurred_on ?? format(new Date(v.created_at), 'yyyy-MM-dd')}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="panel p-4">
              <div className="flex items-center gap-2 section-title mb-3">
                <Network size={15} /> 온톨로지
              </div>
              {entities.length === 0 ? (
                <p className="text-xs text-ax-muted">추출된 엔티티가 없습니다.</p>
              ) : (
                <>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {entities.map((e) => (
                      <span key={e.id} className="badge-purple" title={e.type}>{e.name}</span>
                    ))}
                  </div>
                  <div className="space-y-1">
                    {relations.map((r, i) => (
                      <div key={i} className="text-[11px] text-ax-muted">
                        <span className="text-ax-text">{r.subject}</span>
                        {' '}<span className="text-ax-accent">{r.predicate}</span>{' '}
                        <span className="text-ax-text">{r.object}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
