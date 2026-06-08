import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderKanban, Plus, FileText, Loader2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { projectsApi, type Project } from '../api/client'

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    projectsApi.list()
      .then((r) => setProjects(r.data))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const create = async () => {
    if (!name.trim()) return
    setCreating(true)
    try {
      const r = await projectsApi.create(name.trim(), desc.trim() || undefined)
      setName(''); setDesc('')
      navigate(`/projects/${r.data.slug}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* 새 프로젝트 */}
      <div className="panel p-5 mb-6">
        <div className="section-header">
          <div>
            <div className="section-title">새 프로젝트</div>
            <div className="section-subtitle">위키를 만들 프로젝트를 등록하세요</div>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            className="input flex-1"
            placeholder="프로젝트 이름"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && create()}
          />
          <input
            className="input flex-1"
            placeholder="설명 (선택)"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && create()}
          />
          <button className="btn-primary btn-md" onClick={create} disabled={creating || !name.trim()}>
            {creating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            추가
          </button>
        </div>
      </div>

      {/* 목록 */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-ax-muted gap-2">
          <Loader2 size={18} className="animate-spin" /> 불러오는 중…
        </div>
      ) : projects.length === 0 ? (
        <div className="panel p-10 text-center text-ax-muted">
          <FolderKanban size={32} className="mx-auto mb-3 opacity-40" />
          아직 프로젝트가 없습니다. 위에서 첫 프로젝트를 만들어 보세요.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/projects/${p.slug}`)}
              className="panel p-5 text-left hover:shadow-card-hover transition-shadow group"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="w-9 h-9 rounded-lg bg-ax-blue flex items-center justify-center text-ax-accent">
                  <FolderKanban size={18} />
                </div>
                <span className="badge-default">
                  <FileText size={11} /> {p.doc_count ?? 0}
                </span>
              </div>
              <div className="font-semibold text-ax-text group-hover:text-ax-accent transition-colors truncate">
                {p.name}
              </div>
              {p.description && (
                <div className="text-xs text-ax-muted mt-1 line-clamp-2">{p.description}</div>
              )}
              <div className="text-[11px] text-ax-muted mt-3">
                업데이트 {formatDistanceToNow(new Date(p.updated_at), { addSuffix: true })}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
