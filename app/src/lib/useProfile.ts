import { useCallback, useEffect, useRef, useState } from 'react'
import {
  generateProfile,
  getProfile,
  isApiStatus,
  patchProfile,
  type GenerateOptions,
  type Profile,
  type ProfileEdit,
} from './api'

/**
 * Coarse lifecycle the profile screen branches on.
 * - `loading`    — the initial probe is in flight.
 * - `offline`    — backend unreachable on the initial probe.
 * - `empty`      — backend reachable but no profile generated yet (404).
 * - `ready`      — a profile is loaded.
 */
export type ProfileState = 'loading' | 'offline' | 'empty' | 'ready'

export interface UseProfileResult {
  /** Lifecycle state the screen branches on. */
  state: ProfileState
  /** The loaded profile, or `null` until one exists. */
  profile: Profile | null
  /** True while a (slow) generate request is in flight. */
  isGenerating: boolean
  /** Last generate error message, or `null`. */
  generateError: string | null
  /** True when the last generate failed because no vault is connected (409). */
  noVault: boolean
  /** Generate (or regenerate) the portrait. Slow — a model call. `opts` sets the
   * sampling temperature/seed and can force a redraw. */
  generate: (opts?: GenerateOptions) => Promise<void>
  /** Editable sampling knobs for the next redraw; persist across navigation. */
  genTemperature: number
  genSeed: number
  setGenTemperature: (value: number) => void
  setGenSeed: (value: number) => void
  /** Apply edits to claims; optimistic, then reconciled with the server's truth. */
  applyEdits: (edits: ProfileEdit[]) => Promise<void>
}

/**
 * Owns the profile lifecycle: probes `GET /profile` once on mount (a 404 reads
 * as the `empty` state, an unreachable backend as `offline`), exposes a slow
 * `generate` action, and applies claim edits optimistically — mutating the
 * local profile immediately, then reconciling against the `Profile` the PATCH
 * returns as the source of truth. Never throws on read.
 */
export function useProfile(): UseProfileResult {
  const [state, setState] = useState<ProfileState>('loading')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [noVault, setNoVault] = useState(false)
  const [genTemperature, setGenTemperature] = useState(0)
  const [genSeed, setGenSeed] = useState(7)
  const isMountedRef = useRef(true)
  const genInitialisedRef = useRef(false)

  useEffect(() => {
    isMountedRef.current = true
    const probe = async (): Promise<void> => {
      const next = await getProfile()
      if (!isMountedRef.current) return
      if (next === null) {
        // 404 (no profile yet) and offline both read as null here. We can't tell
        // them apart from this call alone; treat as `empty` so the screen offers
        // generation, and let the slow generate surface a real offline error.
        setState('empty')
        return
      }
      setProfile(next)
      setState('ready')
    }
    void probe()
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Seed the editable generation knobs from the first loaded portrait, then let
  // the user drive them. They live in this shared hook so they persist across
  // screen unmount/remount (e.g. switching tabs mid-redraw keeps what you set).
  useEffect(() => {
    if (profile && !genInitialisedRef.current) {
      genInitialisedRef.current = true
      setGenTemperature(Math.round(profile.temperature * 10) / 10)
      setGenSeed(profile.seed)
    }
  }, [profile])

  const generate = useCallback(async (opts?: GenerateOptions): Promise<void> => {
    setIsGenerating(true)
    setGenerateError(null)
    setNoVault(false)
    try {
      const next = await generateProfile(opts)
      if (!isMountedRef.current) return
      setProfile(next)
      setState('ready')
    } catch (error: unknown) {
      if (!isMountedRef.current) return
      if (isApiStatus(error, 409)) {
        setNoVault(true)
        setGenerateError(null)
        return
      }
      setGenerateError(generateErrorMessage(error))
    } finally {
      if (isMountedRef.current) setIsGenerating(false)
    }
  }, [])

  const applyEdits = useCallback(
    async (edits: ProfileEdit[]): Promise<void> => {
      if (edits.length === 0) return
      // Optimistic: apply locally so the UI responds instantly.
      const previous = profile
      if (previous) {
        setProfile(applyEditsLocally(previous, edits))
      }
      try {
        const next = await patchProfile(edits)
        if (!isMountedRef.current) return
        setProfile(next) // server is the source of truth
      } catch {
        // Roll back to the pre-edit snapshot; a transient failure shouldn't
        // strand the UI in an optimistic state the server never accepted.
        if (isMountedRef.current && previous) setProfile(previous)
      }
    },
    [profile],
  )

  return {
    state,
    profile,
    isGenerating,
    generateError,
    noVault,
    generate,
    genTemperature,
    genSeed,
    setGenTemperature,
    setGenSeed,
    applyEdits,
  }
}

/** Apply a batch of edits to a profile immutably, for the optimistic update. */
function applyEditsLocally(profile: Profile, edits: ProfileEdit[]): Profile {
  const byId = new Map(edits.map((edit) => [edit.id, edit]))
  const claims = profile.claims
    .filter((claim) => !byId.get(claim.id)?.deleted)
    .map((claim) => {
      const edit = byId.get(claim.id)
      if (!edit) return claim
      return {
        ...claim,
        ...(edit.text !== undefined ? { text: edit.text } : {}),
        ...(edit.pinned !== undefined ? { pinned: edit.pinned } : {}),
      }
    })
  return { ...profile, claims }
}

/** Translate a generate failure into a friendly, actionable message. */
function generateErrorMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check ollama is running.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'the portrait could not be drawn — try again.'
}
