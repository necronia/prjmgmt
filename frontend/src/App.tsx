import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import Projects from './pages/Projects'
import ProjectWiki from './pages/ProjectWiki'
import Ingest from './pages/Ingest'
import Search from './pages/Search'
import { bootstrapTheme } from './theme'

function AppInit() {
  useEffect(() => {
    bootstrapTheme()
  }, [])
  return null
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
          </Routes>
        </main>
      </div>
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
