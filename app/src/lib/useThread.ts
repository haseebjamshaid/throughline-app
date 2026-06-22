import { useCallback, useRef, useState } from 'react'
import {
  isApiStatus,
  pullThread,
  threadDidIt,
  threadDifferent,
  threadSmaller,
  type ThreadTurn,
} from './api'

/**
 * Coarse lifecycle the thread screen branches on.
 * - `resting`  — the calm empty page, awaiting the stuck thing.
 * - `pulling`  — a (slow) model call is in flight; show the calm loading state.
 * - `pulled`   — a turn is loaded and being worked with.
 * - `closed`   — the loop is closed (the step was marked done).
 * - `no-vault` — the last pull failed because no vault is connected (409).
 * - `offline`  — the backend is unreachable.
 */
export type ThreadState =
  | 'resting'
  | 'pulling'
  | 'pulled'
  | 'closed'
  | 'no-vault'
  | 'offline'

export interface UseThreadResult {
  /** Lifecycle state the screen branches on. */
  state: ThreadState
  /** The current thread turn, or `null` while resting. */
  turn: ThreadTurn | null
  /** True while any (slow) thread request is in flight. */
  isBusy: boolean
  /** Error message for an unexpected failure, or `null`. */
  error: string | null
  /** Pull a fresh thread from a plain-words stuck statement. Blank is ignored. */
  pull: (stuck: string) => Promise<void>
  /** Ask for a different next step on the current thread. */
  askDifferent: () => Promise<void>
  /** Ask for a smaller next step on the current thread. */
  askSmaller: () => Promise<void>
  /** Mark the current step done — close the loop. */
  markDone: () => Promise<void>
  /** Drop the current thread and return to the resting page. */
  reset: () => void
}

/** Translate a thread request failure into a friendly, lowercase message. */
function threadErrorMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check ollama is running.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'the thread slipped — try again.'
}

/**
 * Owns the thread lifecycle — the heart. A plain-words stuck statement is sent
 * to a slow model call; the returned turn carries one question, one connection
 * from the user's own shelf, and one next step. The step can be made smaller,
 * swapped for a different one, or marked done (closing the loop). Maps a 409 to
 * a dedicated `no-vault` state and an offline failure to `offline` so the screen
 * can guide rather than crash. A request id guards against out-of-order
 * responses from overlapping slow calls. Never throws to the caller.
 */
export function useThread(): UseThreadResult {
  const [state, setState] = useState<ThreadState>('resting')
  const [turn, setTurn] = useState<ThreadTurn | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestIdRef = useRef(0)

  const runStep = useCallback(
    async (
      call: () => Promise<ThreadTurn>,
      pendingState: ThreadState,
    ): Promise<void> => {
      const requestId = ++requestIdRef.current
      setIsBusy(true)
      setError(null)
      setState(pendingState)
      try {
        const next = await call()
        if (requestId !== requestIdRef.current) return
        setTurn(next)
        setState(next.done ? 'closed' : 'pulled')
      } catch (err: unknown) {
        if (requestId !== requestIdRef.current) return
        if (isApiStatus(err, 409)) {
          setState('no-vault')
          return
        }
        if (isApiStatus(err, 0)) {
          setState('offline')
          return
        }
        setState('pulled')
        setError(threadErrorMessage(err))
      } finally {
        if (requestId === requestIdRef.current) setIsBusy(false)
      }
    },
    [],
  )

  const pull = useCallback(
    async (stuck: string): Promise<void> => {
      const trimmed = stuck.trim()
      if (!trimmed) return
      await runStep(() => pullThread(trimmed), 'pulling')
    },
    [runStep],
  )

  const askDifferent = useCallback(async (): Promise<void> => {
    const id = turn?.id
    if (!id) return
    await runStep(() => threadDifferent(id), 'pulling')
  }, [runStep, turn?.id])

  const askSmaller = useCallback(async (): Promise<void> => {
    const id = turn?.id
    if (!id) return
    await runStep(() => threadSmaller(id), 'pulling')
  }, [runStep, turn?.id])

  const markDone = useCallback(async (): Promise<void> => {
    const id = turn?.id
    if (!id) return
    await runStep(() => threadDidIt(id), 'pulling')
  }, [runStep, turn?.id])

  const reset = useCallback((): void => {
    // Invalidate any in-flight slow call so a late response can't revive a turn.
    requestIdRef.current += 1
    setTurn(null)
    setError(null)
    setIsBusy(false)
    setState('resting')
  }, [])

  return {
    state,
    turn,
    isBusy,
    error,
    pull,
    askDifferent,
    askSmaller,
    markDone,
    reset,
  }
}
