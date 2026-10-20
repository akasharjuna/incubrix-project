import './App.css'
import React from 'react'
import { Routes, Route, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { Clapperboard, Plus, LayoutDashboard, ChevronRight, Sun, Moon } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import CreateJob from './pages/CreateJob'
import JobStatus from './pages/JobStatus'
import Results from './pages/Results'

function Navbar() {
  const [isDark, setIsDark] = React.useState(document.documentElement.classList.contains('dark'));
  const toggleTheme = () => {
    document.documentElement.classList.toggle('dark');
    setIsDark(!isDark);
  };
  const navigate = useNavigate();
  const location = useLocation();
  const isCreate = location.pathname === '/create';


  return (
    <header className="sticky top-0 z-50 border-b border-white/6 glass">
      <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between gap-4">

        {/* Wordmark */}
        <NavLink
          to="/"
          className="flex items-center gap-2.5 group shrink-0"
          aria-label="Incubrix home"
        >
          <div className="w-7 h-7 rounded-lg bg-amber-500 flex items-center justify-center shadow-[0_0_10px_rgba(249,127,10,0.3)] group-hover:shadow-[0_0_16px_rgba(249,127,10,0.45)] transition-shadow">
            <Clapperboard size={14} strokeWidth={2.2} className="text-ink-950" />
          </div>
          <span className="font-bold text-[15px] tracking-tight text-white leading-none">
            incubrix
          </span>
        </NavLink>

        {/* Nav links */}
        <nav className="flex items-center gap-0.5">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'text-white bg-white/8'
                  : 'text-ink-400 hover:text-white hover:bg-white/5'
              }`
            }
          >
            <LayoutDashboard size={14} strokeWidth={2} />
            Dashboard
          </NavLink>
        </nav>

        {/* CTA */}
        <button
          id="nav-create-btn"
          onClick={() => navigate('/create')}
          disabled={isCreate}
          className="btn-primary shrink-0 disabled:opacity-60"
        >
          <Plus size={15} strokeWidth={2.5} />
          New Video
        </button>
        {/* Theme toggle */}
        <button
          id="theme-toggle-btn"
          onClick={toggleTheme}
          className="btn-primary shrink-0 ml-2"
          aria-label="Toggle light/dark mode"
        >
          {isDark ? <Sun size={15} strokeWidth={2.5} /> : <Moon size={15} strokeWidth={2.5} />}
        </button>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-5 py-8">
        <Routes>
          <Route path="/"                       element={<Dashboard />} />
          <Route path="/create"                 element={<CreateJob />} />
          <Route path="/jobs/:jobId"            element={<JobStatus />} />
          <Route path="/jobs/:jobId/results"    element={<Results />} />
        </Routes>
      </main>

      <footer className="border-t border-white/6 py-4 px-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-2xs text-ink-500">
          <span>Incubrix B-roll Engine</span>
          <span>Pixabay · gTTS · Whisper · FFmpeg</span>
        </div>
      </footer>
    </div>
  )
}
