// api/v1/broll/[...slug].js – Vercel Serverless function stub
// Handles all /api/v1/broll/* routes used by the frontend.
// Very simple placeholder implementation – returns JSON for the basic endpoints.

export default async function handler(req, res) {
  const { slug = [] } = req.query; // array of path segments after /api/v1/broll
  const method = req.method;
  const path = slug.join('/');

  // Health check
  if (path === 'health') {
    return res.status(200).json({ status: 'ok' });
  }

  // List jobs (GET /api/v1/broll/jobs?limit=n)
  if (path === 'jobs' && method === 'GET') {
    const limit = parseInt(req.query.limit) || 20;
    return res.json({ jobs: [], limit });
  }

  // Create job (POST /api/v1/broll/jobs)
  if (path === 'jobs' && method === 'POST') {
    const body = await req.json();
    const job = { job_id: 'demo-' + Date.now(), status: 'queued', ...body };
    return res.status(201).json(job);
  }

  // Upload audio (POST /api/v1/broll/jobs/upload)
  if (path === 'jobs/upload' && method === 'POST') {
    return res.json({ uploaded: true });
  }

  // Get job details (GET /api/v1/broll/jobs/:id)
  if (slug.length === 2 && slug[0] === 'jobs' && method === 'GET') {
    return res.json({ job_id: slug[1], status: 'completed' });
  }

  // Replace clip (POST /api/v1/broll/jobs/:id/replace-clip)
  if (slug.length === 3 && slug[0] === 'jobs' && slug[2] === 'replace-clip' && method === 'POST') {
    return res.json({ replaced: true, jobId: slug[1] });
  }

  // Artifact URL placeholder (GET /api/v1/broll/jobs/:id/artifacts/:filename)
  if (slug.length === 4 && slug[0] === 'jobs' && slug[2] === 'artifacts' && method === 'GET') {
    const { jobId, filename } = { jobId: slug[1], filename: slug[3] };
    return res.json({ url: `/api/v1/broll/jobs/${jobId}/artifacts/${filename}` });
  }

  // Default fallback
  return res.status(200).json({ message: `Handled ${method} ${path}` });
}
