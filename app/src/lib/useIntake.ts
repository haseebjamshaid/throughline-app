import { useCallback, useEffect, useRef, useState } from 'react'
import {
  INTAKE_PROGRESS_URL,
  pauseIntake,
  parseIntakeProgress,
  resumeIntake,
  startIntake,
  type IntakeProgress,
} from './api'

/** Coarse lifecycle state of an intake (reading) run. */
export type IntakeState = 'idle' | 'running' | 'paused' | 'done' | 'error'

export interface UseIntakeResult {
  /** Lifecycle state used to choose which controls to show. */
  state: IntakeState
  /** Latest streamed progress, or `null` before the first event. */
  progress: IntakeProgress | null
  /** Last action error message, or `null`. */
  error: string | null
  /** Start reading the vault and subscribe to progress. */
  start: () => Promise<void>
  /** Pause the run (keeps streaming so the meter reflects the paused state). */
  pause: () => Promise<void>
  /** Resume a paused run. */
  resume: () => Promise<void>
}

/** True once a progress payload shows every item has been processed. */
function isComplete(progress: IntakeProgress): boolean {
  return progress.total > 0 && progress.done >= progress.total
}

/**
 * Drives the "Read / intake" flow: kicks off `POST /intake/start`, then opens
 * an `EventSource` on the progress stream and surfaces live `done/total` plus
 * the current title. Pause/resume hit their endpoints; the stream keeps the
 * `paused` flag in sync. The stream is closed on completion and on unmount.
 */
export function useIntake(): UseIntakeResult {
  const [state, setState] = useState<IntakeState>('idle')
  const [progress, setProgress] = useState<IntakeProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const isMountedRef = useRef(true)

  const closeStream = useCallback((): void => {
    sourceRef.current?.close()
    sourceRef.current = null
  }, [])

  const subscribe = useCallback((): void => {
    closeStream()
    const source = new EventSource(INTAKE_PROGRESS_URL)
    sourceRef.current = source

    source.onmessage = (event: MessageEvent<string>) => {
      if (!isMountedRef.current) return
      try {
        const next = parseIntakeProgress(JSON.parse(event.data))
        setProgress(next)
        if (isComplete(next)) {
          setState('done')
          closeStream()
        } else {
          setState(next.paused ? 'paused' : 'running')
        }
      } catch {
        // Ignore malformed frames; the next event reconciles.
      }
    }

    source.onerror = () => {
      // The stream ends (or the backend drops) — stop listening. If we never
      // saw a completion, leave the last known state rather than flapping.
      closeStream()
    }
  }, [closeStream])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      closeStream()
    }
  }, [closeStream])

  const start = useCallback(async (): Promise<void> => {
    setError(null)
    setProgress(null)
    setState('running')
    try {
      await startIntake()
      subscribe()
    } catch (err: unknown) {
      if (!isMountedRef.current) return
      setState('error')
      setError(err instanceof Error ? err.message : 'could not start reading.')
    }
  }, [subscribe])

  const pause = useCallback(async (): Promise<void> => {
    try {
      await pauseIntake()
      if (isMountedRef.current) setState('paused')
    } catch (err: unknown) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'could not pause.')
      }
    }
  }, [])

  const resume = useCallback(async (): Promise<void> => {
    try {
      await resumeIntake()
      if (isMountedRef.current) {
        setState('running')
        // Re-subscribe in case the stream closed while paused.
        if (!sourceRef.current) subscribe()
      }
    } catch (err: unknown) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'could not resume.')
      }
    }
  }, [subscribe])

  return { state, progress, error, start, pause, resume }
}
