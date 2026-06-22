import { useCallback, useRef, useState } from 'react'
import {
  isApiStatus,
  postFit,
  postFitDisagree,
  type FitInput,
  type FitResult,
} from './api'

/**
 * Coarse lifecycle the fit screen branches on.
 * - `resting`    — the calm input page, awaiting something to hold up.
 * - `checking`   — a (slow) model call is in flight; show the calm loading state.
 * - `checked`    — a result is loaded and being read.
 * - `no-vault`   — the last check failed because no vault is connected (409).
 * - `no-profile` — connected, but no profile has been generated yet (409).
 * - `offline`    — the backend is unreachable.
 */
export type FitState =
  | 'resting'
  | 'checking'
  | 'checked'
  | 'no-vault'
  | 'no-profile'
  | 'offline'

export interface UseFitResult {
  /** Lifecycle state the screen branches on. */
  state: FitState
  /** The current fit result, or `null` while resting. */
  result: FitResult | null
  /** True while a (slow) fit check is in flight. */
  isBusy: boolean
  /** Error message for an unexpected failure, or `null`. */
  error: string | null
  /** Check the fit of one thing against the profile. */
  check: (input: FitInput) => Promise<void>
  /** Push back on a rule ("that's me on purpose") — hides it + remembers it. */
  disagree: (rule: string) => Promise<void>
  /** Drop the current result and return to the resting page. */
  reset: () => void
}

/** Translate a fit request failure into a friendly, lowercase message. */
function fitErrorMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check ollama is running.'
  }
  if (isApiStatus(error, 400)) {
    return 'add something to hold up first — a few words, or an image.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'the read slipped — try again.'
}

/**
 * Owns the fit-check lifecycle. Something is held up against the user's profile
 * via a slow model call; the returned result carries a 0–100 closeness score,
 * one honest verdict, a checklist tied to the user's own claims, and the closest
 * things from their shelf. A 409 maps to `no-vault` or `no-profile` (told apart
 * by the backend detail) so the screen can guide rather than crash; an offline
 * failure maps to `offline`. Disagreeing with a check hides it optimistically and
 * remembers it on the backend. A request id guards against out-of-order
 * responses from overlapping slow calls. Never throws to the caller.
 */
export function useFit(): UseFitResult {
  const [state, setState] = useState<FitState>('resting')
  const [result, setResult] = useState<FitResult | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const requestIdRef = useRef(0)

  const check = useCallback(async (input: FitInput): Promise<void> => {
    const requestId = ++requestIdRef.current
    setIsBusy(true)
    setError(null)
    setState('checking')
    try {
      const next = await postFit(input)
      if (requestId !== requestIdRef.current) return
      setResult(next)
      setState('checked')
    } catch (err: unknown) {
      if (requestId !== requestIdRef.current) return
      if (isApiStatus(err, 409)) {
        const detail = err instanceof Error ? err.message : ''
        setState(detail.includes('profile') ? 'no-profile' : 'no-vault')
        return
      }
      if (isApiStatus(err, 0)) {
        setState('offline')
        return
      }
      setState('resting')
      setError(fitErrorMessage(err))
    } finally {
      if (requestId === requestIdRef.current) setIsBusy(false)
    }
  }, [])

  const disagree = useCallback(async (rule: string): Promise<void> => {
    // Hide the check immediately (immutably) — the pushback is acknowledged in
    // the UI even if the persistence call later fails.
    setResult((prev) =>
      prev ? { ...prev, checks: prev.checks.filter((c) => c.rule !== rule) } : prev,
    )
    try {
      await postFitDisagree(rule)
    } catch {
      // Best-effort: the rule stays hidden locally for this result regardless.
    }
  }, [])

  const reset = useCallback((): void => {
    // Invalidate any in-flight slow call so a late response can't revive a result.
    requestIdRef.current += 1
    setResult(null)
    setError(null)
    setIsBusy(false)
    setState('resting')
  }, [])

  return { state, result, isBusy, error, check, disagree, reset }
}
