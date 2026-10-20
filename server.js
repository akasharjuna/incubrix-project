// server.js – simple Express stub for the B‑Roll API
// This file lives in the project root (d:/Incubrix Project)
// It provides the endpoints that the frontend expects.
// You can extend it with real logic later.

const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors()); // allow requests from Vercel or localhost
app.use(express.json());

// Health check – used by the frontend
app.get('/api/v1/broll/health', (req, res) => {
  res.json({ status: 'ok' });
});

// List recent jobs (dummy data)
app.get('/api/v1/broll/jobs', (req, res) => {
  const limit = parseInt(req.query.limit) || 20;
  res.json({ jobs: [], limit });
});

// Create a job – echo back payload
app.post('/api/v1/broll/jobs', (req, res) => {
  const job = { job_id: 'demo-' + Date.now(), status: 'queued', ...req.body };
  res.status(201).json(job);
});

// Upload audio – placeholder (just returns success)
app.post('/api/v1/broll/jobs/upload', (req, res) => {
  res.json({ uploaded: true });
});

// Get a specific job – placeholder
app.get('/api/v1/broll/jobs/:jobId', (req, res) => {
  res.json({ job_id: req.params.jobId, status: 'completed' });
});

// Replace clip – placeholder
app.post('/api/v1/broll/jobs/:jobId/replace-clip', (req, res) => {
  res.json({ replaced: true, jobId: req.params.jobId });
});

// Serve artifact URLs (just echo the filename)
app.get('/api/v1/broll/jobs/:jobId/artifacts/:filename', (req, res) => {
  const { jobId, filename } = req.params;
  res.json({ url: `/api/v1/broll/jobs/${jobId}/artifacts/${filename}` });
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`🔧 B‑Roll backend stub listening on http://localhost:${PORT}`);
});
