import { useEffect, useRef, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Loader2, Sparkles, Paperclip, X, ArrowRight, UploadCloud,
  FileText, Image as ImageIcon, FileSpreadsheet, Presentation, File as FileIcon,
} from 'lucide-react'
import { ingestApi, projectsApi, type IngestResult, type Project } from '../api/client'

function fileIcon(name: string) {
  const n = name.toLowerCase()
  if (/\.(png|jpe?g|gif|webp|bmp)$/.test(n)) return ImageIcon
  if (n.endsWith('.pdf')) return FileText
  if (n.endsWith('.pptx') || n.endsWith('.ppt')) return Presentation
  if (n.endsWith('.xlsx') || n.endsWith('.xls') || n.endsWith('.csv')) return FileSpreadsheet
  if (n.endsWith('.docx') || n.endsWith('.doc')) return FileText
  return FileIcon
}

function humanSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function Ingest() {
  const [params] = useSearchParams()
  const [projects, setProjects] = useState<Project[]>([])
  const [projectSlug, setProjectSlug] = useState(params.get('project') ?? '')
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<IngestResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { projectsApi.list().then((r) => setProjects(r.data)) }, [])

  const addFiles = (incoming: FileList | File[]) => {
    const arr = Array.from(incoming)
    if (arr.length) setFiles((prev) => [...prev, ...arr])
  }
  const removeFile = (i: number) => setFiles((prev) => prev.filter((_, idx) => idx !== i))

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files)
  }

  // 클립보드 붙여넣기: 파일/이미지는 첨부, 텍스트는 입력칸으로 (기본 동작 유지)
  const onPaste = (e: React.ClipboardEvent) => {
    const dt = e.clipboardData
    const pasted: File[] = []
    for (const item of Array.from(dt.items)) {
      if (item.kind === 'file') {
        const f = item.getAsFile()
        if (f) pasted.push(f)
      }
    }
    if (pasted.length) {
      e.preventDefault()
      addFiles(pasted)
    }
  }

  const submit = async () => {
    if (!text.trim() && files.length === 0) return
    setLoading(true); setError(null); setResults([])
    try {
      const r = await ingestApi.submit({
        text: text.trim() || undefined,
        project_slug: projectSlug || undefined,
        files,
      })
      setResults(r.data)
      setText(''); setFiles([])
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '처리 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto" onPaste={onPaste}>
      <div className="panel p-5 mb-5">
        <div className="section-header">
          <div>
            <div className="section-title">자료 추가</div>
            <div className="section-subtitle">자연어로 쓰거나, 파일(PDF·PPT·Word·Excel·이미지 등)을 드래그/붙여넣기 하세요. AI가 읽어서 위키로 정리합니다.</div>
          </div>
        </div>

        <div className="mb-3">
          <label className="text-xs text-ax-muted">프로젝트</label>
          <select className="input mt-1" value={projectSlug} onChange={(e) => setProjectSlug(e.target.value)}>
            <option value="">자동 추정 (AI가 판단)</option>
            {projects.map((p) => <option key={p.id} value={p.slug}>{p.name}</option>)}
          </select>
        </div>

        <textarea
          className="input min-h-[140px] font-normal resize-y"
          placeholder="메모를 자연어로 입력하거나, 긴 텍스트를 붙여넣으세요. (파일과 함께 쓰면 파일 정리에 참고됩니다)"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        {/* 드롭존 */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          className={`mt-3 border-2 border-dashed rounded-xl px-4 py-6 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-ax-accent bg-ax-blue' : 'border-ax-border hover:border-ax-accent/50 hover:bg-ax-subtle'
          }`}
        >
          <UploadCloud size={22} className="mx-auto mb-2 text-ax-muted" />
          <div className="text-sm text-ax-text font-medium">파일을 드래그하거나 클릭해서 선택</div>
          <div className="text-xs text-ax-muted mt-0.5">여러 개 가능 · 클립보드 이미지/파일 붙여넣기(⌘V) 지원 · PDF, PPTX, DOCX, XLSX, 이미지, 텍스트</div>
          <input
            ref={fileRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = '' }}
          />
        </div>

        {/* 첨부 목록 */}
        {files.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {files.map((f, i) => {
              const Icon = fileIcon(f.name)
              return (
                <div key={i} className="flex items-center gap-2 panel-flat px-3 py-2">
                  <Icon size={15} className="text-ax-accent flex-shrink-0" />
                  <span className="text-sm text-ax-text truncate flex-1">{f.name}</span>
                  <span className="text-[11px] text-ax-muted flex-shrink-0">{humanSize(f.size)}</span>
                  <button onClick={(e) => { e.stopPropagation(); removeFile(i) }} className="text-ax-muted hover:text-ax-danger flex-shrink-0">
                    <X size={14} />
                  </button>
                </div>
              )
            })}
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <button className="btn-ghost btn-sm" onClick={() => fileRef.current?.click()}>
            <Paperclip size={14} /> 파일 첨부
          </button>
          <button className="btn-primary btn-md" onClick={submit} disabled={loading || (!text.trim() && files.length === 0)}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {files.length > 1 ? `${files.length}개 정리해서 추가` : '정리해서 추가'}
          </button>
        </div>
        {error && <div className="mt-3 text-sm text-ax-danger">{error}</div>}
        {loading && files.length > 0 && (
          <div className="mt-2 text-xs text-ax-muted">파일을 읽고 정리하는 중입니다… (파일 수에 따라 시간이 걸릴 수 있어요)</div>
        )}
      </div>

      {/* 결과 (프로젝트별 카드) — 위키에 병합됨 + 이번 변경 요약 */}
      {results.map((result) => (
        <div key={result.project.id} className="panel p-6 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 min-w-0">
              <span className="badge-green flex-shrink-0">위키 업데이트됨</span>
              <span className="text-sm font-semibold text-ax-text truncate">{result.project.name}</span>
            </div>
            <Link to={`/projects/${result.project.slug}`} className="btn-ghost btn-sm flex-shrink-0">
              위키 보기 <ArrowRight size={14} />
            </Link>
          </div>
          <div className="panel-pastel p-3 mb-1">
            <div className="text-xs text-ax-muted mb-1">이번에 반영된 변경</div>
            <article className="prose-wiki text-sm text-ax-text leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.change_summary}</ReactMarkdown>
            </article>
          </div>
          {result.entities.length > 0 && (
            <div className="mt-4 pt-4 border-t border-ax-border">
              <div className="text-xs text-ax-muted mb-2">엔티티</div>
              <div className="flex flex-wrap gap-1.5">
                {result.entities.map((e) => <span key={e.id} className="badge-purple">{e.name}</span>)}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
