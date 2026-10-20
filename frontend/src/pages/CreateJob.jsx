import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, Mic, LayoutList, ChevronRight,
  Plus, Trash2, Upload, AlertCircle, Loader2, X, Info
} from 'lucide-react'
import { api } from '../services/api'

const ASPECT_RATIOS = [
  { value: '16:9', label: 'Landscape', w: 32, h: 18 },
  { value: '9:16', label: 'Portrait',  w: 18, h: 32 },
  { value: '1:1',  label: 'Square',    w: 24, h: 24 },
]

// ── Aspect Ratio Selector ────────────────────────────────────────────────────
function AspectRatioSelector({ selected, onChange }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {ASPECT_RATIOS.map(({ value, label, w, h }) => {
        const active = selected.includes(value)
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(active ? selected.filter(x => x !== value) : [...selected, value])}
            className={`flex flex-col items-center gap-2 px-4 py-3 rounded-xl border text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 ${
              active
                ? 'border-amber-500/70 bg-amber-500/8 text-amber-400 shadow-[0_0_0_1px_rgba(249,127,10,0.2)]'
                : 'border-white/8 bg-ink-900 text-ink-400 hover:border-white/16 hover:text-ink-200'
            }`}
          >
            {/* Frame preview */}
            <div
              className={`rounded border-2 transition-colors ${active ? 'border-amber-400' : 'border-ink-500'}`}
              style={{ width: w, height: h }}
            />
            <span className="leading-none">{label}</span>
            <span className={`text-2xs leading-none ${active ? 'text-amber-500/70' : 'text-ink-600'}`}>{value}</span>
          </button>
        )
      })}
    </div>
  )
}

// ── Toggle Switch ─────────────────────────────────────────────────────────────
function Toggle({ checked, onChange, disabled = false, id }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative w-9 h-5 rounded-full border transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 disabled:opacity-40 disabled:cursor-not-allowed ${
        checked ? 'bg-amber-500 border-amber-400' : 'bg-ink-700 border-white/10'
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

// ── Field label ────────────────────────────────────────────────────────────────
function Label({ htmlFor, children, hint }) {
  return (
    <label htmlFor={htmlFor} className="block mb-2">
      <span className="text-sm font-medium text-white/80">{children}</span>
      {hint && <span className="ml-2 text-xs text-ink-500">{hint}</span>}
    </label>
  )
}

// ── Error box ─────────────────────────────────────────────────────────────────
function ErrorBox({ msg }) {
  if (!msg) return null
  return (
    <div className="flex items-start gap-2.5 text-rose-400 text-sm bg-rose-900/15 border border-rose-800/40 rounded-xl px-4 py-3">
      <AlertCircle size={15} className="shrink-0 mt-0.5" />
      <span>{msg}</span>
    </div>
  )
}

// ── Script Tab ────────────────────────────────────────────────────────────────
function ScriptTab({ onSubmit, loading }) {
  const [script, setScript] = useState('')
  const [aspectRatios, setAspectRatios] = useState(['16:9'])
  const [captionsEnabled, setCaptionsEnabled] = useState(true)
  const [burnIn, setBurnIn] = useState(true)
  const [avoidList, setAvoidList] = useState('')
  const [error, setError] = useState('')

  const wordCount = script.trim().split(/\s+/).filter(Boolean).length
  const estimatedSec = Math.round(wordCount / 2.4)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!script.trim()) { setError('Script cannot be empty.'); return }
    if (aspectRatios.length === 0) { setError('Select at least one aspect ratio.'); return }
    setError('')
    await onSubmit({
      script: script.trim(),
      aspect_ratios: aspectRatios,
      captions: { enabled: captionsEnabled, burn_in: burnIn },
      avoid_list: avoidList.split(',').map(s => s.trim()).filter(Boolean),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <div className="flex items-baseline justify-between mb-2">
          <Label htmlFor="script-input">Narration script</Label>
          <span className="text-2xs text-ink-500 tabular">
            {wordCount > 0 ? `${wordCount} words · ~${estimatedSec}s` : 'Start typing…'}
          </span>
        </div>
        <textarea
          id="script-input"
          className="input min-h-44 font-mono text-[13px] leading-relaxed"
          placeholder={`Write your narration here. Be descriptive — it helps the footage matching engine.\n\nExample:\nThe Amazon rainforest covers over 5.5 million square kilometres of South America. Towering trees filter the sunlight into dappled green light on the forest floor.`}
          value={script}
          onChange={e => setScript(e.target.value)}
        />
      </div>

      <div>
        <Label>Output format</Label>
        <AspectRatioSelector selected={aspectRatios} onChange={setAspectRatios} />
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-ink-900 border border-white/6">
          <div>
            <p className="text-sm text-white/80 font-medium">Captions</p>
            <p className="text-2xs text-ink-500 mt-0.5">Generate SRT subtitle file</p>
          </div>
          <Toggle id="captions-toggle" checked={captionsEnabled} onChange={setCaptionsEnabled} />
        </div>
        <div className={`flex items-center justify-between py-2.5 px-3 rounded-xl border transition-colors ${captionsEnabled ? 'bg-ink-900 border-white/6' : 'bg-ink-900/50 border-white/4 opacity-50'}`}>
          <div>
            <p className={`text-sm font-medium ${captionsEnabled ? 'text-white/80' : 'text-ink-500'}`}>Burn-in captions</p>
            <p className="text-2xs text-ink-500 mt-0.5">Embed captions directly into video</p>
          </div>
          <Toggle id="burnin-toggle" checked={burnIn} onChange={setBurnIn} disabled={!captionsEnabled} />
        </div>
      </div>

      <div>
        <Label htmlFor="avoid-input" hint="comma-separated">Avoid list</Label>
        <input
          id="avoid-input"
          type="text"
          className="input"
          placeholder="e.g. violence, weapons, alcohol"
          value={avoidList}
          onChange={e => setAvoidList(e.target.value)}
        />
      </div>

      <ErrorBox msg={error} />

      <button id="submit-script-btn" type="submit" disabled={loading} className="btn-primary w-full py-3 text-base">
        {loading
          ? <><Loader2 size={17} className="animate-spin" /> Generating video…</>
          : <><ChevronRight size={17} strokeWidth={2.5} /> Generate Video</>
        }
      </button>
    </form>
  )
}

// ── Audio Tab ─────────────────────────────────────────────────────────────────
function AudioTab({ onSubmitUrl, onSubmitFile, loading }) {
  const [mode, setMode] = useState('url')
  const [audioUrl, setAudioUrl] = useState('')
  const [file, setFile] = useState(null)
  const [aspectRatios, setAspectRatios] = useState(['16:9'])
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (mode === 'url') {
      if (!audioUrl.trim()) { setError('Please enter an audio URL.'); return }
      await onSubmitUrl({ audio_url: audioUrl.trim(), aspect_ratios: aspectRatios, captions: { enabled: true, burn_in: true }, avoid_list: [] })
    } else {
      if (!file) { setError('Please select an audio file.'); return }
      const fd = new FormData()
      fd.append('audio_file', file)
      fd.append('aspect_ratios', aspectRatios.join(','))
      await onSubmitFile(fd)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Sub-tabs */}
      <div className="flex gap-1 p-1 bg-ink-900 border border-white/6 rounded-xl">
        {[['url', 'Audio URL'], ['file', 'Upload file']].map(([m, label]) => (
          <button key={m} type="button" onClick={() => setMode(m)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${mode === m ? 'bg-ink-800 text-white shadow-sm' : 'text-ink-400 hover:text-white'}`}>
            {label}
          </button>
        ))}
      </div>

      {mode === 'url' ? (
        <div>
          <Label htmlFor="audio-url-input">Audio URL</Label>
          <input id="audio-url-input" type="url" className="input"
            placeholder="https://example.com/narration.mp3"
            value={audioUrl} onChange={e => setAudioUrl(e.target.value)} />
          <p className="text-2xs text-ink-500 mt-2">Supported: MP3, WAV, M4A · Max 10 minutes</p>
        </div>
      ) : (
        <div>
          <Label>Audio file</Label>
          <div
            className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
              dragOver ? 'border-amber-500/70 bg-amber-500/5' :
              file ? 'border-amber-500/40 bg-amber-500/3' : 'border-white/10 hover:border-white/20'
            }`}
            onClick={() => !file && inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); setFile(e.dataTransfer.files[0]) }}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <Mic size={18} className="text-amber-400 shrink-0" />
                <span className="text-sm text-white font-medium truncate max-w-48">{file.name}</span>
                <button type="button" onClick={(e) => { e.stopPropagation(); setFile(null) }}
                  className="text-ink-500 hover:text-rose-400 transition-colors">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={24} className="text-ink-600 mx-auto mb-3" />
                <p className="text-sm text-ink-300 mb-1">Drag & drop or <span className="text-amber-400 underline">browse</span></p>
                <p className="text-2xs text-ink-500">MP3, WAV, M4A · Max 100 MB · 10 min</p>
              </>
            )}
            <input ref={inputRef} id="audio-file-input" type="file" accept=".mp3,.wav,.m4a"
              className="hidden" onChange={e => setFile(e.target.files[0])} />
          </div>
        </div>
      )}

      <div>
        <Label>Output format</Label>
        <AspectRatioSelector selected={aspectRatios} onChange={setAspectRatios} />
      </div>

      <ErrorBox msg={error} />

      <button id="submit-audio-btn" type="submit" disabled={loading} className="btn-primary w-full py-3 text-base">
        {loading
          ? <><Loader2 size={17} className="animate-spin" /> Processing audio…</>
          : <><ChevronRight size={17} strokeWidth={2.5} /> Process Audio</>
        }
      </button>
    </form>
  )
}

// ── Scenes Tab ─────────────────────────────────────────────────────────────────
function ScenesTab({ onSubmit, loading }) {
  const [scenes, setScenes] = useState([{ text: '', visual_hint: '' }])
  const [aspectRatios, setAspectRatios] = useState(['16:9'])
  const [error, setError] = useState('')

  const addScene = () => setScenes([...scenes, { text: '', visual_hint: '' }])
  const removeScene = i => setScenes(scenes.filter((_, idx) => idx !== i))
  const update = (i, field, val) =>
    setScenes(scenes.map((s, idx) => idx === i ? { ...s, [field]: val } : s))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const valid = scenes.filter(s => s.text.trim())
    if (!valid.length) { setError('Add at least one scene with text.'); return }
    setError('')
    await onSubmit({
      scenes: valid.map(s => ({ text: s.text.trim(), visual_hint: s.visual_hint.trim() || undefined })),
      aspect_ratios: aspectRatios,
      captions: { enabled: true, burn_in: true },
      avoid_list: [],
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-3">
        {scenes.map((scene, i) => (
          <div key={i} className="relative bg-ink-900 border border-white/8 rounded-xl p-4 group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xs font-bold text-amber-500/80 uppercase tracking-widest">
                Scene {i + 1}
              </span>
              {scenes.length > 1 && (
                <button type="button" onClick={() => removeScene(i)}
                  className="opacity-0 group-hover:opacity-100 text-ink-500 hover:text-rose-400 transition-all p-1 rounded">
                  <Trash2 size={13} />
                </button>
              )}
            </div>
            <textarea
              className="input min-h-16 resize-none text-sm mb-2.5"
              placeholder="Narration text for this scene…"
              value={scene.text}
              onChange={e => update(i, 'text', e.target.value)}
            />
            <input
              type="text"
              className="input text-sm"
              placeholder="Visual hint (optional) — e.g. solar panels on rooftop"
              value={scene.visual_hint}
              onChange={e => update(i, 'visual_hint', e.target.value)}
            />
          </div>
        ))}
      </div>

      <button type="button" onClick={addScene}
        className="btn-secondary w-full py-2.5 justify-center">
        <Plus size={14} /> Add scene
      </button>

      <div>
        <Label>Output format</Label>
        <AspectRatioSelector selected={aspectRatios} onChange={setAspectRatios} />
      </div>

      <ErrorBox msg={error} />

      <button id="submit-scenes-btn" type="submit" disabled={loading} className="btn-primary w-full py-3 text-base">
        {loading
          ? <><Loader2 size={17} className="animate-spin" /> Generating…</>
          : <><ChevronRight size={17} strokeWidth={2.5} /> Generate Video</>
        }
      </button>
    </form>
  )
}

// ── Tips sidebar ──────────────────────────────────────────────────────────────
function TipsSidebar({ activeTab }) {
  const tips = {
    script: [
      'Longer, vivid sentences give the matcher more to work with.',
      'Paragraphs become separate scenes — use line breaks deliberately.',
      'Avoid List prevents certain categories from appearing in footage.',
    ],
    audio: [
      'Whisper transcribes your audio and splits it into scenes.',
      'Clear speech with minimal background noise gives best results.',
      'Max 100 MB · 10 minutes per upload.',
    ],
    scenes: [
      'Visual hints directly guide the footage search for each scene.',
      'Keep each scene to one focused idea for best matching.',
      'You can swap alternative clips from the Results page.',
    ],
  }

  return (
    <div className="panel h-fit sticky top-24">
      <p className="label mb-3 flex items-center gap-1.5">
        <Info size={11} className="text-amber-500" />
        Tips
      </p>
      <ul className="space-y-3">
        {(tips[activeTab] || []).map((tip, i) => (
          <li key={i} className="flex items-start gap-2.5 text-xs text-ink-400 leading-relaxed">
            <span className="w-1 h-1 rounded-full bg-amber-500/60 mt-1.5 shrink-0" />
            {tip}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function CreateJob() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('script')
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const TABS = [
    { id: 'script', label: 'Script',  Icon: FileText },
    { id: 'audio',  label: 'Audio',   Icon: Mic },
    { id: 'scenes', label: 'Scenes',  Icon: LayoutList },
  ]

  const handleResult = job => navigate(`/jobs/${job.job_id}`)

  const submit = async (payload) => {
    setLoading(true); setSubmitError('')
    try { const job = await api.createJob(payload); handleResult(job) }
    catch (e) { setSubmitError(e.message); setLoading(false) }
  }

  const submitFile = async (formData) => {
    setLoading(true); setSubmitError('')
    try { const job = await api.uploadAudio(formData); handleResult(job) }
    catch (e) { setSubmitError(e.message); setLoading(false) }
  }

  return (
    <div className="animate-fade-up max-w-5xl mx-auto">
      {/* Page header */}
      <div className="mb-7">
        <h1 className="heading-1 mb-1">New video</h1>
        <p className="text-sm text-ink-400">Choose an input method and configure your output.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-6">
        {/* Form column */}
        <div>
          {/* Input mode tabs */}
          <div className="tab-group mb-5">
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                id={`tab-${id}`}
                onClick={() => setTab(id)}
                className={`tab-item ${tab === id ? 'tab-item-active' : 'tab-item-inactive'}`}
              >
                <Icon size={14} strokeWidth={2} />
                {label}
              </button>
            ))}
          </div>

          {/* Form panel */}
          <div className="panel-lg">
            {submitError && <div className="mb-5"><ErrorBox msg={submitError} /></div>}
            {tab === 'script' && <ScriptTab onSubmit={submit} loading={loading} />}
            {tab === 'audio'  && <AudioTab onSubmitUrl={submit} onSubmitFile={submitFile} loading={loading} />}
            {tab === 'scenes' && <ScenesTab onSubmit={submit} loading={loading} />}
          </div>
        </div>

        {/* Tips sidebar */}
        <TipsSidebar activeTab={tab} />
      </div>
    </div>
  )
}
