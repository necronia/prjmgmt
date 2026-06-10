import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Loader2, History, Network, FileText, Plus, Pencil, MessageSquare, Save, X, Tag, Info, Send,
} from 'lucide-react'
import { format } from 'date-fns'
import { projectsApi, type WikiDoc, type Revision, type Entity, type Relation, type Project, type MetaItem } from '../api/client'

export default function ProjectWiki() {
  const { slug } = useParams<{ slug: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [doc, setDoc] = useState<WikiDoc | null>(null)
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [entities, setEntities] = useState<Entity[]>([])
  const [relations, setRelations] = useState<Relation[]>([])
  const [loading, setLoading] = useState(true)

  const [mode, setMode] = useState<null | 'manual' | 'chat'>(null)
  const [draftContent, setDraftContent] = useState('')
  const [draftMeta, setDraftMeta] = useState<MetaItem[]>([])
  const [saving, setSaving] = useState(false)
  const [chatMsg, setChatMsg] = useState('')
  const [chatBusy, setChatBusy] = useState(false)

  const load = () => {
    if (!slug) return
    setMode(null)  // 프로젝트 이동 시 편집 모드/초안 초기화
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
  }
  useEffect(load, [slug])

  const openManual = () => {
    setDraftContent(doc?.content_md ?? '')
    setDraftMeta(doc?.meta ?? [])
    setMode('manual')
  }
  const saveManual = async () => {
    if (!slug) return
    setSaving(true)
    try {
      await projectsApi.editDocument(slug, draftContent, draftMeta.filter((m) => m.label || m.value))
      setMode(null)
      load()
    } finally { setSaving(false) }
  }
  const sendChat = async () => {
    if (!slug || !chatMsg.trim()) return
    setChatBusy(true)
    try {
      await projectsApi.editConversational(slug, chatMsg.trim())
      setChatMsg(''); setMode(null)
      load()
    } finally { setChatBusy(false) }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-ax-muted gap-2">
      <Loader2 size={18} className="animate-spin" /> 불러오는 중…
    </div>
  }
  if (!project) return <div className="p-6 text-ax-muted">프로젝트를 찾을 수 없습니다.</div>

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="page-header">
        <div className="min-w-0">
          <h2 className="page-title truncate">{project.name}</h2>
          {doc && <p className="section-subtitle">최종 수정 {format(new Date(doc.updated_at), 'yyyy-MM-dd HH:mm')}</p>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {doc && mode === null && (
            <>
              <button className="btn-secondary btn-sm" onClick={() => setMode('chat')}>
                <MessageSquare size={14} /> 대화로 수정
              </button>
              <button className="btn-secondary btn-sm" onClick={openManual}>
                <Pencil size={14} /> 직접 수정
              </button>
            </>
          )}
          <Link to={`/ingest?project=${project.slug}`} className="btn-primary btn-sm">
            <Plus size={14} /> 자료 추가
          </Link>
        </div>
      </div>

      {/* 대화식 수정 바 */}
      {mode === 'chat' && (
        <div className="panel p-4 mb-4">
          <div className="flex items-center gap-2 section-title mb-2"><MessageSquare size={15} /> 대화로 수정</div>
          <div className="flex gap-2">
            <input
              autoFocus
              className="input flex-1"
              placeholder="예) 사업기간을 7월까지로 바꿔줘 / 테스트 5차 완료로 업데이트"
              value={chatMsg}
              onChange={(e) => setChatMsg(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendChat()}
            />
            <button className="btn-primary btn-md" onClick={sendChat} disabled={chatBusy || !chatMsg.trim()}>
              {chatBusy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} 적용
            </button>
            <button className="btn-ghost btn-md" onClick={() => setMode(null)} disabled={chatBusy}><X size={16} /></button>
          </div>
          <p className="text-xs text-ax-muted mt-2">지시한 내용이 위키에 병합되고 검색·온톨로지에 반영됩니다.</p>
        </div>
      )}

      {!doc ? (
        <div className="panel p-10 text-center text-ax-muted">
          <FileText size={32} className="mx-auto mb-3 opacity-40" />
          아직 위키가 없습니다. <Link to={`/ingest?project=${project.slug}`} className="text-ax-accent">자료 추가</Link>로 시작하세요.
        </div>
      ) : mode === 'manual' ? (
        /* 수동 편집기 */
        <div className="panel p-6 space-y-4">
          <div>
            <div className="flex items-center gap-2 section-title mb-2"><Info size={15} /> 프로젝트 정보 (메타)</div>
            <div className="space-y-2">
              {draftMeta.map((m, i) => (
                <div key={i} className="flex gap-2">
                  <input className="input-sm w-40 flex-shrink-0" placeholder="항목 (예: 고객사)" value={m.label}
                    onChange={(e) => setDraftMeta(draftMeta.map((x, j) => j === i ? { ...x, label: e.target.value } : x))} />
                  <input className="input-sm flex-1" placeholder="값" value={m.value}
                    onChange={(e) => setDraftMeta(draftMeta.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} />
                  <button className="btn-ghost btn-sm" onClick={() => setDraftMeta(draftMeta.filter((_, j) => j !== i))}><X size={14} /></button>
                </div>
              ))}
              <button className="btn-ghost btn-sm" onClick={() => setDraftMeta([...draftMeta, { label: '', value: '' }])}>
                <Plus size={14} /> 항목 추가
              </button>
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2 section-title mb-2"><FileText size={15} /> 본문 (마크다운)</div>
            <textarea className="input min-h-[360px] font-mono text-xs resize-y" value={draftContent}
              onChange={(e) => setDraftContent(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <button className="btn-ghost btn-md" onClick={() => setMode(null)} disabled={saving}>취소</button>
            <button className="btn-primary btn-md" onClick={saveManual} disabled={saving}>
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} 저장
            </button>
          </div>
          <p className="text-xs text-ax-muted">저장 시 카테고리·온톨로지·검색 인덱스가 자동 재반영됩니다.</p>
        </div>
      ) : (
        /* 보기 모드 */
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
          <div className="min-w-0 space-y-4">
            {/* 프로젝트 정보 (메타) */}
            {doc.meta.length > 0 && (
              <div className="panel p-5">
                <div className="flex items-center gap-2 section-title mb-3"><Info size={15} /> 프로젝트 정보</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2.5">
                  {doc.meta.map((m, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <span className="text-ax-muted w-24 flex-shrink-0">{m.label}</span>
                      <span className="text-ax-text font-medium">{m.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 카테고리 분류 */}
            {doc.categories.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap px-1">
                <Tag size={14} className="text-ax-muted" />
                {doc.categories.map((c) => <span key={c} className="badge-blue">{c}</span>)}
              </div>
            )}

            {/* 진행 내용 */}
            <div className="panel p-6">
              <article className="prose-wiki text-sm text-ax-text leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.content_md}</ReactMarkdown>
              </article>
            </div>
          </div>

          {/* 사이드: 수정 이력 + 온톨로지 */}
          <div className="space-y-4 min-w-0">
            <div className="panel p-4">
              <div className="flex items-center gap-2 section-title mb-3"><History size={15} /> 수정 이력 ({revisions.length})</div>
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
              <div className="flex items-center gap-2 section-title mb-3"><Network size={15} /> 온톨로지</div>
              {entities.length === 0 ? (
                <p className="text-xs text-ax-muted">추출된 엔티티가 없습니다.</p>
              ) : (
                <>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {entities.map((e) => <span key={e.id} className="badge-purple" title={e.type}>{e.name}</span>)}
                  </div>
                  <div className="space-y-1">
                    {relations.map((r, i) => (
                      <div key={i} className="text-[11px] text-ax-muted">
                        <span className="text-ax-text">{r.subject}</span>{' '}
                        <span className="text-ax-accent">{r.predicate}</span>{' '}
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
