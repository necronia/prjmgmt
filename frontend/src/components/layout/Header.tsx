import { useLocation, useParams } from 'react-router-dom'
import { Menu } from 'lucide-react'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/':        { title: 'Projects',  subtitle: '관리 중인 프로젝트 위키 목록' },
  '/ingest':  { title: 'Ingest',    subtitle: '자연어·텍스트·이미지로 자료 추가' },
  '/search':  { title: 'Search',    subtitle: '자연어로 질문하고 근거와 함께 답을 받기' },
}

export function Header({ onMenuClick }: { onMenuClick?: () => void }) {
  const location = useLocation()
  const params = useParams()
  const page = location.pathname.startsWith('/projects/')
    ? { title: params.slug ?? 'Wiki', subtitle: '프로젝트 위키 — 버전 맥락 유지' }
    : (PAGE_TITLES[location.pathname] ?? { title: 'PrjMgmt', subtitle: '' })

  return (
    <header className="h-14 border border-ax-border rounded-2xl shadow-[0_1px_3px_rgba(15,23,42,0.06)] flex items-center justify-between px-4 md:px-6 bg-ax-shell backdrop-blur-sm flex-shrink-0">
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          onClick={onMenuClick}
          className="md:hidden flex-shrink-0 w-9 h-9 -ml-1 rounded-lg flex items-center justify-center text-ax-muted hover:text-ax-text hover:bg-ax-subtle transition-colors"
          aria-label="메뉴 열기"
        >
          <Menu size={20} />
        </button>
        <div className="flex flex-col justify-center min-w-0">
          <h1 className="text-sm font-bold text-ax-text leading-none truncate">{page.title}</h1>
          {page.subtitle && (
            <p className="text-xs text-ax-muted mt-0.5 hidden sm:block truncate">{page.subtitle}</p>
          )}
        </div>
      </div>
    </header>
  )
}
