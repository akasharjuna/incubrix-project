import { useParams, useNavigate } from 'react-router-dom'
import {
  Loader, CheckCircle, XCircle, Clock, ChevronRight,
  Film, Mic, LayoutList, RefreshCw, AlertCircle
} from 'lucide-react'
import { useJobPolling } from '../hooks/useJobPolling'

const STAGE_LABELS = {
  validating: 'Validating input',
  transcribing: 'Transcribing audio',
  segmenting: 'Segmenting script',
  generating_audio: 'Generating narration',
  matching_footage: 'Matching B-roll footage',
  downloading_clips: 'Downloading clips',
  rendering: 'Rendering video',
  generating_captions: 'Generating captions',
  finalizing: 'Finalizing artifacts',
  done: 'Complete',
}

const ALL_STAGES = Object.keys(STAGE_LABELS)

function StageTimeline({ currentStage, status }) {
  const currentIdx = ALL_STAGES.indexOf(currentStage)
  return (
    <div className="space-y-2">
      {ALL_STAGES.filter(s => s !== 'done').map((stage, i) => {
        const isDone = status === 'completed' || i < currentIdx
        const isCurrent = stage === currentStage && status === 'processing'
        const isPending = i > currentIdx
        return (
          <div key={stage} className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all ${
            isCurrent ? 'bg-amber-600/15 border border-amber-500/30' :
            isDone ? 'opacity-50' : 'opacity-25'
          }`}>
            <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
              isDone ? 'bg-green-700' :
              isCurrent ? 'bg-accent-600 animate-pulse' :
              'bg-dark-600'
            }`}>
              {isDone ? <CheckCircle size={12} className="text-green-300" /> :
               isCurrent ? <Loader size={11} className="text-white animate-spin" /> :
               <div className="w-1.5 h-1.5 rounded-full bg-gray-600" />}
            </div>
            <span className={`text-sm ${isCurrent ? 'text-white font-medium' : isDone ? 'text-gray-300' : 'text-gray-500'}`}>
              {STAGE_LABELS[stage]}
            </span>
            {isCurrent && (
              <span className="ml-auto text-xs text-amber-400 animate-pulse">In progress…</span>
            )}
            {isDone && (
              <span className="ml-auto text-xs text-emerald-500">Done</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function JobStatus() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { job, loading, error } = useJobPolling(jobId, 2000)

  if (loading && !job) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader size={28} className="animate-spin text-amber-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto card border-red-900/40 text-center py-12">
        <XCircle size={36} className="text-red-400 mx-auto mb-3" />
        <p className="text-red-400 font-semibold mb-1">Connection Error</p>
        <p className="text-gray-500 text-sm">{error}</p>
      </div>
    )
  }

  if (!job) return null

  const modeIcon = { script: Film, audio: Mic, scenes: LayoutList }
  const ModeIcon = modeIcon[job.input_mode] || Film

  // Redirect to results when done
  if (job.status === 'completed') {
    return (
      <div className="max-w-lg mx-auto animate-in">
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-green-900/40 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} className="text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Video Ready! 🎉</h2>
          <p className="text-gray-400 text-sm mb-6">
            Your video has been rendered with {job.scenes?.length || 0} scenes.
          </p>
          <button
            id="view-results-btn"
            onClick={() => navigate(`/jobs/${jobId}/results`)}
            className="btn-primary mx-auto"
          >
            <ChevronRight size={17} /> View Results
          </button>
        </div>
      </div>
    )
  }

  if (job.status === 'failed') {
    return (
      <div className="max-w-lg mx-auto animate-in">
        <div className="card border-red-900/40 text-center py-12">
          <div className="w-16 h-16 bg-red-900/40 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle size={32} className="text-red-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Job Failed</h2>
          <p className="text-red-400 text-sm mb-2">{job.error_message || 'An unknown error occurred.'}</p>
          {job.warnings?.length > 0 && (
            <div className="mt-4 text-left bg-dark-700 rounded-lg p-4">
              {job.warnings.map((w, i) => (
                <p key={i} className="text-yellow-400 text-xs mb-1">⚠ {w}</p>
              ))}
            </div>
          )}
          <button onClick={() => navigate('/create')} className="btn-secondary mx-auto mt-6">
            <RefreshCw size={15} /> Try Again
          </button>
        </div>
      </div>
    )
  }

  // Processing
  const percent = job.progress?.percent ?? 0
  const stage = job.progress?.stage ?? 'validating'
  const message = job.progress?.message ?? 'Processing...'
  const scenesTotal = job.progress?.scenes_total ?? 0
  const scenesDone = job.progress?.scenes_done ?? 0

  return (
    <div className="max-w-lg mx-auto animate-in">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <ModeIcon size={18} className="text-amber-400" />
          <h1 className="text-xl font-bold text-white">Processing Video</h1>
        </div>
        <p className="text-xs text-gray-500 font-mono">Job: {jobId}</p>
      </div>

      {/* Progress ring + percent */}
      <div className="card mb-5">
        <div className="flex items-center gap-5 mb-4">
          <div className="relative w-16 h-16 flex-shrink-0">
            <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
              <circle cx="32" cy="32" r="28" stroke="#2d2d4e" strokeWidth="6" fill="none" />
              <circle
                cx="32" cy="32" r="28"
                stroke="#8b5cf6"
                strokeWidth="6"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 28}`}
                strokeDashoffset={`${2 * Math.PI * 28 * (1 - percent / 100)}`}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
              {percent}%
            </span>
          </div>
          <div>
            <p className="font-semibold text-white text-sm">{message}</p>
            {scenesTotal > 0 && (
              <p className="text-xs text-gray-400 mt-1">
                Matching scenes: {scenesDone}/{scenesTotal}
              </p>
            )}
            <p className="text-xs text-gray-600 mt-0.5 font-mono">
              Stage: {STAGE_LABELS[stage] || stage}
            </p>
          </div>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${percent}%` }} />
        </div>
      </div>

      {/* Stage timeline */}
      <div className="card">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Pipeline Stages</p>
        <StageTimeline currentStage={stage} status={job.status} />
      </div>

      {job.warnings?.length > 0 && (
        <div className="mt-4 card border-yellow-900/40">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={14} className="text-yellow-400" />
            <span className="text-xs font-semibold text-yellow-400">Warnings</span>
          </div>
          {job.warnings.map((w, i) => (
            <p key={i} className="text-yellow-400/80 text-xs mb-1">{w}</p>
          ))}
        </div>
      )}
    </div>
  )
}
