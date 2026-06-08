import { useEffect, useRef, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Loader2, Sparkles, Image as ImageIcon, X, ArrowRight } from 'lucide-react'
import { ingestApi, projectsApi, type IngestResult, type Project } from '../api/client'

export default function Ingest() {
  const [params] = useSearchParams()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectSlug, setProjectSlug] = useState(params.get('project') ?? '')
  const [text, setText] = useState('')
  const [image, setImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<IngestResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { projectsApi.list().then((r) => setProjects(r.data)) }, [])

  const onFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => setImage(reader.result as string)
    reader.readAsDataURL(file)
  }

  const submit = async () => {
    if (!text.trim() && !image) return
    setLoading(true); setError(null); setResult(null)
    try {
      const r = await ingestApi.submit({
        text: text.trim() || undefined,
        image_base64: image ?? undefined,
        project_slug: projectSlug || undefined,
      })
      setResult(r.data)
      setText(''); setImage(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '처리 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="panel p-5 mb-5">
        <div className="section-header">
          <div>
            <div className="section-title">자료 추가</div>
            <div className="section-subtitle">자연어로 쓰거나, 긴 텍스트를 붙여넣거나, 이미지를 첨부하세요. AI가 읽어서 위키에 정리합니다.</div>
          </div>
        </div>

        <div className="mb-3">
          <label className="text-xs text-ax-muted">프로젝트</label>
          <select
            className="input mt-1"
            value={projectSlug}
            onChange={(e) => setProjectSlug(e.target.value)}
          >
            <option value="">자동 추정 (AI가 판단)</option>
            {projects.map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
        </div>

        <textarea
          className="input min-h-[180px] font-normal resize-y"
          placeholder="예) JARVIS 프로젝트에 OpenRouter 폴백 로직을 추가했고, rate limit 시 7개 모델을 순차 시도하도록 바꿈. 오늘 테스트 통과."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        {/* 이미지 첨부 */}
        <div className="mt-3 flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
          <button className="btn-secondary btn-sm" onClick={() => fileRef.current?.click()}>
            <ImageIcon size={14} /> 이미지 첨부
          </button>
          {image && (
            <span className="badge-default">
              첨부됨
              <button onClick={() => setImage(null)} className="ml-1"><X size={11} /></button>
            </span>
          )}
        </div>
        {image && <img src={image} alt="preview" className="mt-3 max-h-48 rounded-lg border border-ax-border" />}

        <div className="mt-4 flex justify-end">
          <button className="btn-primary btn-md" onClick={submit} disabled={loading || (!text.trim() && !image)}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            정리해서 추가
          </button>
        </div>
        {error && <div className="mt-3 text-sm text-ax-danger">{error}</div>}
      </div>

      {/* 결과 미리보기 */}
      {result && (
        <div className="panel p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="badge-green">추가됨</span>
              <span className="text-sm font-semibold text-ax-text">{result.document.title}</span>
            </div>
            <Link to={`/projects/${result.project.slug}`} className="btn-ghost btn-sm">
              {result.project.name} 위키로 <ArrowRight size={14} />
            </Link>
          </div>
          <article className="prose-wiki text-sm text-ax-text leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.document.content_md}</ReactMarkdown>
          </article>
          {result.entities.length > 0 && (
            <div className="mt-4 pt-4 border-t border-ax-border">
              <div className="text-xs text-ax-muted mb-2">추출된 엔티티</div>
              <div className="flex flex-wrap gap-1.5">
                {result.entities.map((e) => <span key={e.id} className="badge-purple">{e.name}</span>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
