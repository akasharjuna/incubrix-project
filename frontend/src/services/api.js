/**
 * API service — all backend calls go through this module.
 */
const API_BASE = '/api/v1/broll'

async function request(method, path, body = null, isFormData = false) {
  const opts = {
    method,
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
  }
  if (body) {
    opts.body = isFormData ? body : JSON.stringify(body)
  }
  const resp = await fetch(path, opts)
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  // Create job with JSON body (script / audio_url / scenes)
  createJob: (payload) => request('POST', `${API_BASE}/jobs`, payload),

  // Upload audio file
  uploadAudio: (formData) => request('POST', `${API_BASE}/jobs/upload`, formData, true),

  // Get job status
  getJob: (jobId) => request('GET', `${API_BASE}/jobs/${jobId}`),

  // List recent jobs
  listJobs: (limit = 20) => request('GET', `${API_BASE}/jobs?limit=${limit}`),

  // Replace a clip (explainable matching feature)
  replaceClip: (jobId, body) => request('POST', `${API_BASE}/jobs/${jobId}/replace-clip`, body),

  // Build artifact download URL
  artifactUrl: (jobId, filename) => `${API_BASE}/jobs/${jobId}/artifacts/${filename}`,

  // Health
  health: () => fetch('/health').then(r => r.json()),
}
