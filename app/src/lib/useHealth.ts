import { useEffect, useRef, useState } from 'react'
import { fetchHealth, type HealthStatus } from './api'

/** How often to re-poll the backend health endpoint (ms). */
const POLL_INTERVAL_MS = 5000

export interface UseHealthResult {
  /** Parsed health, or `null` when the backend is offline/unreachable. */
  status: HealthStatus | null
  /** True only when the backend responded successfully to the latest poll. */
  isOnline: boolean
  /** True until the first poll resolves (avoids a flash of "offline"). */
  isLoading: boolean
}

/**
 * Polls `GET /health` on an interval and surfaces backend reachability.
 * Designed to never throw — an unreachable backend simply reads as offline.
 */
export function useHealth(): UseHealthResult {
  const [status, setStatus] = useState<HealthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true

    const poll = async (): Promise<void> => {
      const next = await fetchHealth()
      if (!isMountedRef.current) return
      setStatus(next)
      setIsLoading(false)
    }

    void poll()
    const intervalId = setInterval(() => void poll(), POLL_INTERVAL_MS)

    return () => {
      isMountedRef.current = false
      clearInterval(intervalId)
    }
  }, [])

  return {
    status,
    isOnline: status !== null,
    isLoading,
  }
}
