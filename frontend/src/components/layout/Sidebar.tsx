import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { FolderKanban, PlusCircle, Search, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { reviewsApi } from '../../api/client'

const navItems = [
  { to: '/', icon: FolderKanban, label: 'Projects', end: true },
  { to: '/ingest', icon: PlusCircle, label: 'Ingest', end: false },
  { to: '/search', icon: Search, label: 'Search', end: false },
]

export function Sidebar({ className = '', onNavigate }: { className?: string; onNavigate?: () => void }) {
  const location = useLocation()
  const [reviewCount, setReviewCount] = useState(0)

  useEffect(() => {
    reviewsApi.count().then((r) => setReviewCount(r.data.count)).catch(() => {})
  }, [location.pathname])

  return (
    <aside className={clsx(
      'w-60 h-full bg-ax-shell border border-ax-border rounded-2xl shadow-[0_1px_3px_rgba(15,23,42,0.06)] flex-col flex-shrink-0 overflow-hidden',
      className,
    )}>
      {/* Brand */}
      <div className="h-14 px-4 border-b border-ax-border flex items-center flex-shrink-0">
        <span className="text-sm font-bold text-ax-text tracking-tight">Project</span>
        <span className="text-sm font-bold text-ax-accent tracking-tight ml-1">Wiki</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 mt-1">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) => clsx(isActive ? 'nav-item-active' : 'nav-item-inactive')}
          >
            <Icon size={17} className="flex-shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}

        {/* 확인 필요 (배지) */}
        <NavLink
          to="/review"
          onClick={onNavigate}
          className={({ isActive }) => clsx(isActive ? 'nav-item-active' : 'nav-item-inactive', 'justify-between')}
        >
          <span className="flex items-center gap-3">
            <AlertCircle size={17} className="flex-shrink-0" />
            <span>확인 필요</span>
          </span>
          {reviewCount > 0 && (
            <span className="text-[11px] font-semibold bg-ax-danger text-white rounded-full px-1.5 min-w-[18px] text-center">
              {reviewCount}
            </span>
          )}
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-ax-border">
        <p className="text-xs text-ax-muted">PrjMgmt · v0.1.0</p>
      </div>
    </aside>
  )
}
