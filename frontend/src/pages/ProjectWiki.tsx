import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Loader2, History, Network, FileText, Plus } from 'lucide-react'
import { format } from 'date-fns'
import { projectsApi, type WikiDoc, type Revision, type Entity, type Relation, type Project } from '../api/client'

export default function ProjectWiki() {
  const { slug } = useParams<{ slug: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [doc, setDoc] = useState<WikiDoc | null>(null)
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [relations, setRelations] = useState<Relation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!slug) return
    setLoading(true)
    projectsApi.get(slug)
      .then((r) => {
        setProject(r.data.project)
        setDoc(r.data.document)
        setRevisions(r.data.revisions)
        setEntities(r.data.entities)
        setRelations(r.data.relations)
      })
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-ax-muted gap-2">
      <Loader2 size={18} className="animate-spin" /> 불러오는 중…
    </div>
  }
  if (!project) return <div className="p-6 text-ax-muted">프로젝트를 찾을 수 없습니다.</div>

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="page-header">
        <div>
          <h2 className="page-title">{project.name}</h2>
          {project.description && <p className="section-subtitle">{project.description}</p>}
          {doc && (
            <p className="section-subtitle">최종 수정 {format(new Date(doc.updated_at), 'yyyy-MM-dd HH:mm')}</p>
          )}
        </div>
        <Link to={`/ingest?project=${project.slug}`} className="btn-primary btn-md">
          <Plus size={16} /> 자료 추가
        </Link>
      </div>

      {!doc ? (
        <div className="panel p-10 text-center text-ax-muted">
          <FileText size={32} className="mx-auto mb-3 opacity-40" />
          아직 위키가 없습니다. <Link to={`/ingest?project=${project.slug}`} className="text-ax-accent">자료 추가</Link>로 시작하세요.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
          {/* 단일 위키 본문 (계속 업데이트됨) */}
          <div className="panel p-6 min-w-0">
            <article className="prose-wiki text-sm text-ax-text leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.content_md}</ReactMarkdown>
            </article>
          </div>

          {/* 사이드: 수정 이력 + 온톨로지 */}
          <div className="space-y-4 min-w-0">
            <div className="panel p-4">
              <div className="flex items-center gap-2 section-title mb-3">
                <History size={15} /> 수정 이력 ({revisions.length})
              </div>
              <div className="space-y-2.5">
                {revisions.map((rev) => (
                  <div key={rev.id} className="border-l-2 border-ax-border pl-3">
                    <div className="text-[11px] text-ax-muted flex items-center gap-1.5">
                      {rev.occurred_on ?? format(new Date(rev.created_at), 'yyyy-MM-dd')}
                      <span className="badge-default">{rev.source_type}</span>
                    </div>
                    <div className="text-sm text-ax-text mt-0.5">{rev.summary}</div>
                  </div>
                ))}
                {revisions.length === 0 && <p className="text-xs text-ax-muted">수정 이력이 없습니다.</p>}
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
