import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Download, Film, FileText, Info, ChevronDown, ChevronUp,
  RefreshCw, ArrowLeft, Star, CheckCircle, AlertTriangle,
  ExternalLink, Loader, Zap, BarChart2
} from 'lucide-react'
import { useJobPolling } from '../hooks/useJobPolling'
import { api } from '../services/api'

// ── Score Bar ────────────────────────────────────────────────────────────────
function ScoreBar({ score }) {
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-dark-600 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

// ── Scene Card ───────────────────────────────────────────────────────────────
function SceneCard({ scene, jobId, onClipReplaced }) {
  const [expanded, setExpanded] = useState(false)
  const [replacing, setReplacing] = useState(false)
  const [replaceError, setReplaceError] = useState('')

  const handleReplace = async (altClip) => {
    setReplacing(true)
    setReplaceError('')
    try {
      await api.replaceClip(jobId, {
        scene_id: scene.scene_id,
        asset_id: altClip.asset_id,
        reason: 'User selected alternative clip from results page',
      })
      onClipReplaced?.()
    } catch (e) {
      setReplaceError(e.message)
    } finally {
      setReplacing(false)
    }
  }

  const clip = scene.clip
  const score = scene.relevance_score ?? 0
  const scorePct = Math.round(score * 100)

  return (
    <div className={`card border transition-all ${scene.fallback_used ? 'border-yellow-800/40' : 'border-surface-border'}`}>
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="w-7 h-7 bg-accent-600/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
          <span className="text-xs font-bold text-accent-400">
            {scene.scene_id?.replace('scene-', '') || '?'}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200 leading-snug">{scene.text}</p>
          {scene.visual_hint && (
            <p className="text-xs text-gray-500 mt-1 italic">Hint: {scene.visual_hint}</p>
          )}
        </div>
        {scene.fallback_used && (
          <span className="badge bg-yellow-900/40 text-yellow-400 flex-shrink-0">Fallback</span>
        )}
      </div>

      {/* Timing */}
      <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
        <span>{scene.start?.toFixed(1)}s → {scene.end?.toFixed(1)}s</span>
        <span>({((scene.end ?? 0) - (scene.start ?? 0)).toFixed(1)}s)</span>
      </div>

      {/* Clip info */}
      {clip ? (
        <div className="bg-dark-700 rounded-lg p-3 mb-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Film size={13} className="text-amber-400" />
              <span className="text-xs font-medium text-gray-300 truncate max-w-48">
                {clip.asset_id}
              </span>
            </div>
            <a
              href={clip.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-accent-400 transition-colors"
            >
              <ExternalLink size={12} />
            </a>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
            <span className="bg-dark-600 px-1.5 py-0.5 rounded">{clip.provider}</span>
            <span>{clip.duration?.toFixed(1)}s</span>
            <span>{clip.width}×{clip.height}</span>
            {clip.license && (
              <span className="text-green-500">{clip.license.name}</span>
            )}
          </div>

          {/* Relevance score */}
          <div className="mb-1.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">Relevance</span>
              <span className={`text-xs font-semibold ${scorePct >= 70 ? 'text-green-400' : scorePct >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                {scorePct}%
              </span>
            </div>
            <ScoreBar score={score} />
          </div>
        </div>
      ) : (
        <div className="bg-yellow-900/20 border border-yellow-800/40 rounded-lg p-3 mb-3 text-xs text-yellow-400">
          <AlertTriangle size={13} className="inline mr-1" />
          No clip assigned — {scene.fallback_reason || 'footage unavailable'}
        </div>
      )}

      {/* Selection reason (expandable) */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left text-xs text-gray-500 flex items-center gap-1 hover:text-gray-300 transition-colors"
      >
        <Zap size={12} className="text-amber-500" />
        <span>Why this clip?</span>
        {expanded ? <ChevronUp size={12} className="ml-auto" /> : <ChevronDown size={12} className="ml-auto" />}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 animate-in">
          <div className="bg-dark-700 rounded-lg p-3 text-xs text-gray-400 leading-relaxed">
            {scene.selection_reason || 'No selection reason recorded.'}
          </div>

          {scene.search_queries?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Search queries used:</p>
              <div className="flex flex-wrap gap-1.5">
                {scene.search_queries.map((q, i) => (
                  <span key={i} className="text-xs bg-dark-600 text-gray-400 px-2 py-0.5 rounded-full">{q}</span>
                ))}
              </div>
            </div>
          )}

          {scene.recovery_attempts?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Recovery log:</p>
              {scene.recovery_attempts.map((r, i) => (
                <p key={i} className="text-xs text-yellow-500/70 mb-0.5">• {r}</p>
              ))}
            </div>
          )}

          {/* Alternative clips */}
          {scene.alternative_clips?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-2">Alternative clips:</p>
              <div className="space-y-2">
                {scene.alternative_clips.map(alt => (
                  <div key={alt.asset_id} className="flex items-center gap-2 bg-dark-800 rounded-lg p-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-300 truncate">{alt.asset_id}</p>
                      <p className="text-xs text-gray-600">{alt.provider} · {alt.duration?.toFixed(1)}s</p>
                    </div>
                    <button
                      onClick={() => handleReplace(alt)}
                      disabled={replacing}
                      className="btn-secondary text-xs px-2.5 py-1"
                    >
                      {replacing ? <Loader size={11} className="animate-spin" /> : 'Use This'}
                    </button>
                  </div>
                ))}
              </div>
              {replaceError && (
                <p className="text-xs text-red-400 mt-2">{replaceError}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Results Page ─────────────────────────────────────────────────────────────
export default function Results() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { job, loading, refetch } = useJobPolling(jobId, 5000)
  const [activeAr, setActiveAr] = useState('16:9')
  const [activeTab, setActiveTab] = useState('video')

  if (loading && !job) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader size={28} className="animate-spin text-amber-400" />
      </div>
    )
  }

  if (!job) return null

  // If re-rendering after clip replace
  if (job.status === 'processing') {
    return (
      <div className="max-w-lg mx-auto text-center py-20 animate-in">
        <Loader size={32} className="animate-spin text-amber-400 mx-auto mb-4" />
        <p className="text-white font-semibold">Re-rendering video…</p>
        <p className="text-gray-500 text-sm mt-1">{job.progress?.message}</p>
        <div className="progress-bar mt-4 max-w-xs mx-auto">
          <div className="progress-fill" style={{ width: `${job.progress?.percent ?? 0}%` }} />
        </div>
      </div>
    )
  }

  const artifacts = job.artifacts || {}
  const scenes = job.scenes || []
  const totalDuration = scenes.length > 0
    ? Math.max(...scenes.map(s => s.end ?? 0)).toFixed(1)
    : '—'
  const avgScore = scenes.length > 0
    ? (scenes.reduce((acc, s) => acc + (s.relevance_score ?? 0), 0) / scenes.length * 100).toFixed(0)
    : 0

  const arFileMap = {
    '16:9': artifacts.video_16_9,
    '9:16': artifacts.video_9_16,
    '1:1': artifacts.video_1_1,
  }
  const availableArs = Object.entries(arFileMap).filter(([, f]) => f).map(([ar]) => ar)
  const currentFile = arFileMap[activeAr]

  return (
    <div className="animate-in">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/')} className="btn-ghost">
          <ArrowLeft size={16} /> Back
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Video Results</h1>
          <p className="text-xs text-gray-500 font-mono">{jobId}</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Scenes', value: scenes.length },
          { label: 'Duration', value: `${totalDuration}s` },
          { label: 'Avg. Relevance', value: `${avgScore}%` },
          { label: 'Fallbacks', value: scenes.filter(s => s.fallback_used).length },
        ].map(s => (
          <div key={s.label} className="card py-3 text-center">
            <p className="text-xl font-bold text-accent-400">{s.value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left — Video + Downloads */}
        <div className="lg:col-span-3 space-y-4">
          {/* Aspect ratio selector */}
          {availableArs.length > 1 && (
            <div className="flex gap-2">
              {availableArs.map(ar => (
                <button key={ar} id={`ar-btn-${ar.replace(':', '_')}`}
                  onClick={() => setActiveAr(ar)}
                  className={`tab text-xs ${activeAr === ar ? 'tab-active' : 'tab-inactive'}`}>
                  {ar}
                </button>
              ))}
            </div>
          )}

          {/* Video player */}
          <div className="card p-0 overflow-hidden bg-black">
            {currentFile ? (
              <video
                key={currentFile}
                controls
                className="w-full"
                style={{ maxHeight: '360px' }}
                src={api.artifactUrl(jobId, currentFile)}
              >
                Your browser does not support video playback.
              </video>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-600">
                <Film size={40} className="opacity-30" />
              </div>
            )}
          </div>

          {/* Downloads */}
          <div className="card">
            <p className="text-sm font-semibold text-gray-300 mb-3">Downloads</p>
            <div className="space-y-2">
              {availableArs.map(ar => {
                const file = arFileMap[ar]
                if (!file) return null
                return (
                  <a
                    key={ar}
                    id={`download-${ar.replace(':', '_')}`}
                    href={api.artifactUrl(jobId, file)}
                    download={file}
                    className="flex items-center gap-3 p-3 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                  >
                    <Film size={16} className="text-amber-400" />
                    <div>
                      <p className="text-sm text-gray-200 font-medium">{file}</p>
                      <p className="text-xs text-gray-500">{ar} MP4</p>
                    </div>
                    <Download size={14} className="ml-auto text-gray-500" />
                  </a>
                )
              })}
              {artifacts.captions_srt && (
                <a
                  href={api.artifactUrl(jobId, artifacts.captions_srt)}
                  download={artifacts.captions_srt}
                  className="flex items-center gap-3 p-3 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                >
                  <FileText size={16} className="text-amber-400" />
                  <div>
                    <p className="text-sm text-gray-200 font-medium">captions.srt</p>
                    <p className="text-xs text-gray-500">SRT Subtitles</p>
                  </div>
                  <Download size={14} className="ml-auto text-gray-500" />
                </a>
              )}
              {artifacts.timeline_json && (
                <a
                  href={api.artifactUrl(jobId, artifacts.timeline_json)}
                  download="timeline.json"
                  className="flex items-center gap-3 p-3 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                >
                  <BarChart2 size={16} className="text-amber-400" />
                  <div>
                    <p className="text-sm text-gray-200 font-medium">timeline.json</p>
                    <p className="text-xs text-gray-500">Scene timeline & provenance</p>
                  </div>
                  <Download size={14} className="ml-auto text-gray-500" />
                </a>
              )}
              {artifacts.manifest_json && (
                <a
                  href={api.artifactUrl(jobId, artifacts.manifest_json)}
                  download="manifest.json"
                  className="flex items-center gap-3 p-3 bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors"
                >
                  <Info size={16} className="text-green-400" />
                  <div>
                    <p className="text-sm text-gray-200 font-medium">manifest.json</p>
                    <p className="text-xs text-gray-500">Full job manifest & checksums</p>
                  </div>
                  <Download size={14} className="ml-auto text-gray-500" />
                </a>
              )}
            </div>
          </div>

          {/* Warnings */}
          {job.warnings?.length > 0 && (
            <div className="card border-yellow-900/40">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={14} className="text-yellow-400" />
                <span className="text-sm font-semibold text-yellow-400">Warnings ({job.warnings.length})</span>
              </div>
              {job.warnings.map((w, i) => (
                <p key={i} className="text-yellow-400/80 text-xs mb-1">• {w}</p>
              ))}
            </div>
          )}
        </div>

        {/* Right — Scene analysis */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-300">
              Scene Matching
              <span className="ml-2 text-amber-400 text-xs font-normal">
                <Zap size={11} className="inline" /> Explainable
              </span>
            </p>
            <button onClick={refetch} className="btn-ghost text-xs">
              <RefreshCw size={12} /> Refresh
            </button>
          </div>

          {scenes.length === 0 ? (
            <div className="card text-center py-8 text-gray-600 text-sm">No scene data available.</div>
          ) : (
            <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
              {scenes.map(scene => (
                <SceneCard
                  key={scene.scene_id}
                  scene={scene}
                  jobId={jobId}
                  onClipReplaced={refetch}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
