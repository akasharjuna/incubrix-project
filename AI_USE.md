# AI_USE.md

## AI coding assistants & tools used in this project

| Tool / Service | Purpose in the IncuBrix project | Notes |
|---|---|---|
| **ChatGPT / Antigravity (OSS‑120B)** | Primary coding assistant that wrote, edited, and reviewed source code, generated the assessment report, and performed Git operations. | All suggestions were reviewed before committing. |
| **Vercel CLI (`vercel`)** | Deploys the frontend static build and the serverless API functions to Vercel. Used to verify that the health‑check endpoint works after each change. | Run via `vercel --prod`. |
| **Whisper (local model)** | Offline speech‑to‑text transcription of audio inputs (up to 10 min). Integrated via the `whisper` Python package. | No external API key required. |
| **gTTS (Google Text‑to‑Speech)** | Generates spoken audio from the script when a language is supported. Used as the default TTS engine. | Fallback to ElevenLabs is optional. |
| **Sentence‑Transformers (`all‑MiniLM‑L6‑v2`)** | Provides semantic embeddings for the relevance‑scoring model in `semantic_matcher.py`. | Lazy‑loaded; fallback to TF‑IDF if the package is missing. |
| **Pixabay API** | Supplies royalty‑free video clips for the B‑roll generation. Integrated via `backend/app/providers/pixabay.py`. | API key stored in `.env`. |
| **Git & GitHub** | Version control and remote hosting of the repository. Used for committing the changes and pushing them to the remote repo. |
| **Docker (optional)** | The `docker-compose.yml` file is present for local development, but the primary workflow runs on Vercel. |
| **FFmpeg** | Stitching audio, video, and adding overlays during the rendering stage. |
| **Python `pydantic` Settings** | Reads configuration from environment variables (`.env`). |

The above list captures every AI‑related service and tooling that contributed to building the **Script → B‑Roll Video Engine**.
