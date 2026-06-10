import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AlertCircle, X } from 'lucide-react'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import Projects from './pages/Projects'
import ProjectWiki from './pages/ProjectWiki'
import Ingest from './pages/Ingest'
import Search from './pages/Search'
import Review from './pages/Review'
import { bootstrapTheme } from './theme'
import { reviewsApi } from './api/client'

function AppInit() {
  useEffect(() => {
    bootstrapTheme()
  }, [])
  return null
}

// 접속 시 '확인 필요' 항목이 있으면 토스트로 알림 (1회)
function ReviewToast() {
  const [count, setCount] = useState(0)
  const [show, setShow] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    reviewsApi.count().then((r) => {
      if (r.data.count > 0) { setCount(r.data.count); setShow(true) }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!show) return
    const t = setTimeout(() => setShow(false), 12000)
    return () => clearTimeout(t)
  }, [show])

  if (!show) return null
  return (
    <div className="fixed bottom-5 right-5 z-50">
      <div className="panel shadow-card-hover p-4 flex items-start gap-3 max-w-sm bg-ax-surface">
        <div className="w-9 h-9 rounded-lg bg-ax-amber flex items-center justify-center text-ax-warning flex-shrink-0">
          <AlertCircle size={18} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ax-text">확인이 필요한 항목 {count}개</div>
          <div className="text-xs text-ax-muted mt-0.5">AI가 정확히 이해하지 못한 내용이 있어요. 알려주시면 위키에 반영됩니다.</div>
          <button
            className="btn-primary btn-sm mt-2"
            onClick={() => { setShow(false); navigate('/review') }}
          >
            확인하러 가기
          </button>
        </div>
        <button className="text-ax-muted hover:text-ax-text flex-shrink-0" onClick={() => setShow(false)}>
          <X size={16} />
        </button>
      </div>
    </div>
  )
}

function AppLayout() {
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  useEffect(() => { setNavOpen(false) }, [location.pathname])

  return (
    <div className="flex h-screen overflow-hidden bg-ax-bg gap-1.5 p-1.5">
      <Sidebar className="hidden md:flex" />

      {/* 모바일 드로어 */}
      <div
        className={`md:hidden fixed inset-0 z-40 transition-opacity duration-200 ${
          navOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        aria-hidden={!navOpen}
      >
        <div className="absolute inset-0 bg-ax-text/40 backdrop-blur-sm" onClick={() => setNavOpen(false)} />
        <div
          className={`absolute left-0 top-0 h-full p-1.5 transition-transform duration-200 ${
            navOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <Sidebar className="flex" onNavigate={() => setNavOpen(false)} />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden gap-1.5">
        <Header onMenuClick={() => setNavOpen(true)} />
        <main className="flex-1 overflow-y-auto bg-ax-shell border border-ax-border rounded-2xl shadow-[0_1px_3px_rgba(15,23,42,0.06)]">
          <Routes>
            <Route path="/" element={<Projects />} />
            <Route path="/projects/:slug" element={<ProjectWiki />} />
            <Route path="/ingest" element={<Ingest />} />
            <Route path="/search" element={<Search />} />
            <Route path="/review" element={<Review />} />
          </Routes>
        </main>
      </div>

      <ReviewToast />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInit />
      <AppLayout />
    </BrowserRouter>
  )
}
