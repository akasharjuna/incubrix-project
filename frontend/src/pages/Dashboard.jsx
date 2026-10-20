import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Film, Clock, CheckCircle, XCircle, Loader2,
  Plus, ArrowUpRight, Clapperboard, Wand2
} from 'lucide-react'
import { api } from '../services/api'

// ── Status Badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const cfg = {
    queued:     { label: 'Queued',     cls: 'badge-queued',     dot: 'bg-ink-400' },
    processing: { label: 'Processing', cls: 'badge-processing', dot: 'bg-sky-400 animate-pulse' },
    completed:  { label: 'Completed',  cls: 'badge-completed',  dot: 'bg-jade-400' },
    failed:     { label: 'Failed',     cls: 'badge-failed',     dot: 'bg-rose-400' },
  }
  const { label, cls, dot } = cfg[status] || cfg.queued
  return (
    <span className={`badge ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} inline-block`} />
      {label}
    </span>
  )
}

// ── Mode label ────────────────────────────────────────────────────────────────
const MODE_LABELS = { script: 'Script', audio: 'Audio', scenes: 'Scenes' }

// ── Job Row (list style) ──────────────────────────────────────────────────────
function JobRow({ job, index }) {
  const navigate = useNavigate()
  const isCompleted = job.status === 'completed'
  const percent = job.progress?.percent ?? 0
  const stage = job.progress?.stage ?? ''

  const handleClick = () =>
    navigate(isCompleted ? `/jobs/${job.job_id}/results` : `/jobs/${job.job_id}`)

  return (
    <button
      onClick={handleClick}
      className="w-full text-left group flex items-center gap-4 px-5 py-4 hover:bg-white/3 transition-colors border-b border-white/5 last:border-0 focus-visible:outline-none focus-visible:bg-white/5"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Icon */}
      <div className="shrink-0 w-9 h-9 rounded-xl bg-ink-800 border border-white/6 flex items-center justify-center">
        <Film size={16} className="text-amber-400" />
      </div>

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-medium text-white truncate">
            {MODE_LABELS[job.input_mode] || 'Video'} Job
          </span>
          <StatusBadge status={job.status} />
        </div>
        {job.status === 'processing' ? (
          <div className="flex items-center gap-2">
            <div className="progress-track flex-1 max-w-32">
              <div className="progress-fill" style={{ width: `${percent}%` }} />
            </div>
            <span className="text-2xs text-ink-400 tabular">{percent}%</span>
            <span className="text-2xs text-ink-500 truncate">{stage.replace('_', ' ')}</span>
          </div>
        ) : (
          <p className="text-xs text-ink-500 truncate font-mono">
            {job.job_id.slice(0, 18)}…
          </p>
        )}
      </div>

      {/* Timestamp */}
      <div className="shrink-0 text-right hidden sm:block">
        <p className="text-xs text-ink-500">
          {new Date(job.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
        </p>
        <p className="text-2xs text-ink-600">
          {new Date(job.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>

      {/* Arrow */}
      <ArrowUpRight
        size={15}
        className="shrink-0 text-ink-600 group-hover:text-amber-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all"
      />
    </button>
  )
}

// ── Stats strip ───────────────────────────────────────────────────────────────
function StatsStrip({ jobs }) {
  const stats = [
    { label: 'Total',      value: jobs.length },
    { label: 'Completed',  value: jobs.filter(j => j.status === 'completed').length },
    { label: 'Processing', value: jobs.filter(j => j.status === 'processing').length },
    { label: 'Failed',     value: jobs.filter(j => j.status === 'failed').length },
  ]
  return (
    <div className="grid grid-cols-4 gap-px bg-white/6 rounded-xl overflow-hidden mb-6">
      {stats.map(s => (
        <div key={s.label} className="bg-ink-900 px-4 py-3 text-center">
          <p className="text-xl font-bold text-white tabular">{s.value}</p>
          <p className="text-2xs text-ink-500 mt-0.5 uppercase tracking-wider">{s.label}</p>
        </div>
      ))}
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listJobs(20)
      .then(data => setJobs(data.jobs || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="animate-fade-up">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="mb-10">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="label mb-2 flex items-center gap-1.5">
              <Wand2 size={11} className="text-amber-500" />
              AI B-roll Engine
            </p>
            <h1 className="heading-1 text-3xl mb-2 text-balance">
              Script to Video,{' '}
              <span className="text-amber-400">automatically.</span>
            </h1>
            <p className="text-ink-400 text-sm max-w-md leading-relaxed">
              Paste a script or voiceover. We segment it, generate narration,
              match real B-roll footage, and export a production-ready video.
            </p>
          </div>
          <button
            id="hero-create-btn"
            onClick={() => navigate('/create')}
            className="btn-primary shrink-0"
          >
            <Plus size={15} strokeWidth={2.5} />
            New Video
          </button>
        </div>

        {/* How it works — minimal 3-step */}
        <div className="flex items-center gap-0 mt-8 text-2xs text-ink-500 flex-wrap gap-y-2">
          {['Write or upload narration', 'AI matches B-roll footage', 'Download your video'].map((s, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <span className="w-6 h-px bg-ink-700 shrink-0" />}
              <span className="flex items-center gap-1.5">
                <span className="w-4 h-4 rounded-full bg-ink-800 border border-white border-opacity-[0.08] text-2xs font-bold text-amber-400 flex items-center justify-center tabular">
                  {i + 1}
                </span>
                {s}
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Jobs section ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="heading-3">Recent Jobs</h2>
        {!loading && jobs.length > 0 && (
          <span className="caption">{jobs.length} job{jobs.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Stats */}
      {!loading && !error && jobs.length > 0 && <StatsStrip jobs={jobs} />}

      {/* Content states */}
      {loading ? (
        <div className="panel">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-0 py-4 border-b border-white/5 last:border-0">
              <div className="skeleton w-9 h-9 rounded-xl" />
              <div className="flex-1 space-y-2">
                <div className="skeleton h-3.5 w-1/3 rounded" />
                <div className="skeleton h-2.5 w-1/2 rounded" />
              </div>
              <div className="skeleton h-3 w-16 rounded hidden sm:block" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="panel border border-rose-900/40 text-center py-12">
          <div className="w-12 h-12 rounded-2xl bg-rose-900/30 border border-rose-800/40 flex items-center justify-center mx-auto mb-4">
            <XCircle size={22} className="text-rose-400" />
          </div>
          <p className="text-sm font-semibold text-rose-400 mb-1">Cannot connect to backend</p>
          <p className="caption">{error}</p>
          <p className="text-2xs text-ink-600 mt-2">Make sure the backend is running on port 8000</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="panel border border-dashed border-white/10">
          <div className="empty-state">
                        <div className="w-14 h-14 rounded-2xl bg-ink-800 border border-white border-opacity-[0.08] flex items-center justify-center mb-4">
              <Clapperboard size={24} className="text-ink-500" />
            </div>
            <p className="text-sm font-semibold text-white mb-1">No videos yet</p>
            <p className="caption mb-5">Create your first video to get started</p>
            <button
              id="empty-create-btn"
              onClick={() => navigate('/create')}
              className="btn-primary"
            >
              <Plus size={15} />
              Create your first video
            </button>
          </div>
        </div>
      ) : (
        <div className="panel p-0 overflow-hidden">
          {jobs.map((job, i) => (
            <JobRow key={job.job_id} job={job} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
