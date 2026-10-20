import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../services/api'

/**
 * Poll a job's status until it reaches a terminal state.
 * Returns { job, loading, error, refetch }
 */
export function useJobPolling(jobId, intervalMs = 2000) {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  const fetch = useCallback(async () => {
    if (!jobId) return
    try {
      const data = await api.getJob(jobId)
      setJob(data)
      setError(null)
      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(intervalRef.current)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    fetch()
    intervalRef.current = setInterval(fetch, intervalMs)
    return () => clearInterval(intervalRef.current)
  }, [jobId, fetch, intervalMs])

  return { job, loading, error, refetch: fetch }
}
