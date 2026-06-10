import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, CheckCircle2, HelpCircle, X, Send, Inbox } from 'lucide-react'
import { reviewsApi, type ReviewItem } from '../api/client'

export default function Review() {
  const [items, setItems] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [busy, setBusy] = useState<number | null>(null)

  const load = () => {
    setLoading(true)
    reviewsApi.list().then((r) => setItems(r.data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const resolve = async (item: ReviewItem) => {
    setBusy(item.id)
    try {
      await reviewsApi.resolve(item.id, (answers[item.id] || '').trim() || undefined)
      setItems((prev) => prev.filter((x) => x.id !== item.id))
    } finally { setBusy(null) }
  }
  const dismiss = async (item: ReviewItem) => {
    setBusy(item.id)
    try {
      await reviewsApi.dismiss(item.id)
      setItems((prev) => prev.filter((x) => x.id !== item.id))
    } finally { setBusy(null) }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="page-header">
        <div>
          <h2 className="page-title">확인 필요</h2>
          <p className="section-subtitle">AI가 정확히 이해하지 못한 항목입니다. 알려주시면 위키에 반영됩니다.</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-ax-muted gap-2">
          <Loader2 size={18} className="animate-spin" /> 불러오는 중…
        </div>
      ) : items.length === 0 ? (
        <div className="panel p-10 text-center text-ax-muted">
          <Inbox size={32} className="mx-auto mb-3 opacity-40" />
          확인이 필요한 항목이 없습니다. 깔끔하네요!
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="panel p-5">
              <div className="flex items-start gap-3">
                <HelpCircle size={18} className="text-ax-warning flex-shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {item.project_slug && (
                      <Link to={`/projects/${item.project_slug}`} className="badge-blue">{item.project_name}</Link>
                    )}
                  </div>
                  <div className="text-sm text-ax-text font-medium">{item.question}</div>
                  {item.context && (
                    <div className="text-xs text-ax-muted mt-1 bg-ax-subtle rounded-md px-2 py-1 break-words">
                      “{item.context}”
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    <input
                      className="input flex-1"
                      placeholder="정확한 내용을 알려주세요 (예: MI룸벽몸 → MI 모델)"
                      value={answers[item.id] ?? ''}
                      onChange={(e) => setAnswers({ ...answers, [item.id]: e.target.value })}
                      onKeyDown={(e) => e.key === 'Enter' && resolve(item)}
                    />
                    <button className="btn-primary btn-md flex-shrink-0" onClick={() => resolve(item)} disabled={busy === item.id}>
                      {busy === item.id ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} 반영
                    </button>
                    <button className="btn-ghost btn-md flex-shrink-0" onClick={() => dismiss(item)} disabled={busy === item.id} title="무시">
                      <X size={16} />
                    </button>
                  </div>
                  <p className="text-[11px] text-ax-muted mt-1.5 flex items-center gap-1">
                    <CheckCircle2 size={11} /> 답변하면 해당 프로젝트 위키에 반영되고 이 항목은 사라집니다. 답변 없이 ✕는 무시.
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
