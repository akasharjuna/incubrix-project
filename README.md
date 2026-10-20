# B-roll Video Engine
### IncuBrix Engineering Assessment — Problem 3

> Convert a written script or uploaded voiceover into a complete, professional video with AI-matched B-roll footage, synchronized captions, and multi-format output.

---

## Features

| Feature | Implementation |
|---|---|
| 3 input modes | Script → TTS, Audio Upload/URL → Whisper STT, Structured Scenes |
| Semantic B-roll matching | sentence-transformers (all-MiniLM-L6-v2) + composite scoring |
| Ambiguity resolution | Bank, cloud, mouse, python, value — context-disambiguated |
| Footage providers | Pexels (real), Mock (deterministic testing) |
| FFmpeg rendering | H.264/AAC, 30fps, burn-in captions, all aspect ratios |
| Output formats | 16:9, 9:16, 1:1 MP4 + SRT captions |
| Artifacts | timeline.json, manifest.json with full provenance |
| Async job processing | Background workers + disk-persisted state, orphan recovery |
| Explainable matching | Per-scene score, selection reason, alternatives, user clip swap |
| OpenAPI docs | http://localhost:8000/docs |

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env — add PEXELS_API_KEY if you have one (optional, mock works without it)
docker compose up --build
```

- Frontend: http://localhost:80
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option B — Local Development (without Docker)

**Prerequisites:**
- Python 3.11+ — `py -3 --version`
- Node.js 20+ — `node --version`
- FFmpeg — [Download from ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

**Backend:**
```bash
cd backend
py -3 -m pip install -r requirements.txt
cp ../.env.example .env
py -3 -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173  
Backend: http://localhost:8000

---

## Architecture

```
project/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # FastAPI routes (jobs.py, health.py)
│   │   ├── core/           # Config, logging
│   │   ├── matching/       # Semantic matcher (sentence-transformers)
│   │   ├── models/         # Job domain models
│   │   ├── providers/      # Footage provider abstraction (Pexels, Mock)
│   │   ├── rendering/      # FFmpeg rendering + caption generator
│   │   ├── schemas/        # Pydantic API schemas
│   │   ├── services/       # TTS, STT, scene segmenter, artifact service
│   │   ├── storage/        # Job store (in-memory + JSON disk persistence)
│   │   └── workers/        # Async job worker (full pipeline)
│   └── tests/              # 40+ tests (no network/API keys required)
├── frontend/
│   └── src/
│       ├── pages/          # Dashboard, CreateJob, JobStatus, Results
│       ├── services/       # API client
│       └── hooks/          # useJobPolling
├── docker-compose.yml
└── .env.example
```

---

## API Reference

### Create Job
```http
POST /api/v1/broll/jobs
Content-Type: application/json

{
  "script": "Solar energy is transforming homes worldwide.",
  "aspect_ratios": ["16:9", "9:16"],
  "captions": { "enabled": true, "burn_in": true },
  "avoid_list": []
}
```

### Upload Audio
```http
POST /api/v1/broll/jobs/upload
Content-Type: multipart/form-data

audio_file=<file>
aspect_ratios=16:9
```

### Get Job Status
```http
GET /api/v1/broll/jobs/{job_id}
```

### Download Artifact
```http
GET /api/v1/broll/jobs/{job_id}/artifacts/{filename}
```

### Replace Clip (Explainable Matching)
```http
POST /api/v1/broll/jobs/{job_id}/replace-clip
{
  "scene_id": "scene-001",
  "asset_id": "mock-007",
  "reason": "Better match for the narration"
}
```

Full OpenAPI spec: http://localhost:8000/docs

---

## Running Tests

```bash
cd backend
py -3 -m pytest tests/ -v
```

Tests use the deterministic mock provider — **no API keys or network access required**.

Test coverage:
- Scene segmentation (empty, single, multi, timing)
- Ambiguity disambiguation (bank, cloud, python, mouse)
- Semantic matching + reuse penalization
- Licensing eligibility
- Caption/SRT generation + timestamp validation
- API input validation (empty, multiple modes, invalid aspect ratio)
- Job state transitions
- Mock provider
- Timeline/manifest JSON validity
- 40+ tests total

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `FOOTAGE_PROVIDER` | `mock` | `mock` or `pexels` |
| `PEXELS_API_KEY` | — | Pexels API key (free at pexels.com) |
| `TTS_PROVIDER` | `gtts` | `gtts` (free) |
| `STT_PROVIDER` | `whisper` | `whisper` (local) or `mock` |
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium` |
| `RENDER_PRESET` | `development` | `development` (480p) or `production` (1080p) |
| `MIN_RELEVANCE_THRESHOLD` | `0.20` | Below this → fallback footage used |

---

## Distinctive Feature: Explainable Scene Matching

Every scene in the Results view shows:
- The selected clip + relevance score (0–100%)
- **Why** this clip was chosen (semantic, hint, duration, aspect-ratio scores)
- Search queries that were used
- Recovery attempts if the top score was below threshold
- Up to 3 alternative clips the user can swap in
- On swap → automatic re-render, timeline/manifest updated

---

## Scoring Model

```
score = 0.60 × semantic_similarity(narration, clip_title)
      + 0.20 × hint_similarity(visual_hint, clip_title)
      + 0.10 × duration_fit_score
      + 0.10 × aspect_ratio_fit_score
```

Scores are model-estimated relevance values, not proven probabilities.
Weights are configurable via environment variables.

---

## Trade-offs

| Decision | Trade-off |
|---|---|
| In-memory + JSON job store | Simple, no Redis needed. Not horizontally scalable. |
| gTTS for TTS | Free, no API key. Slightly robotic voice vs. ElevenLabs. |
| Whisper local STT | Offline. `base` model is fast but less accurate than large. |
| Mock provider default | Works without API keys. Swap `FOOTAGE_PROVIDER=pexels` for real footage. |
| Development render preset | 480p for speed. Set `RENDER_PRESET=production` for 1080p. |
