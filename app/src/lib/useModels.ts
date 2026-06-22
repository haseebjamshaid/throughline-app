import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getModels,
  loadModel,
  unloadAll,
  unloadModel,
  type ModelStatus,
} from './api'

/** How often to re-poll the models endpoint while the panel is open (ms). */
const POLL_INTERVAL_MS = 4000

export interface UseModelsResult {
  /** Latest model statuses, or `null` while the backend is offline/unreachable. */
  models: ModelStatus[] | null
  /** True until the first poll resolves (avoids a flash of "offline"). */
  isLoading: boolean
  /** True only when the backend answered the latest poll. */
  isOnline: boolean
  /** Names currently mid-flight on a load/unload action (toggle disabled). */
  pending: ReadonlySet<string>
  /** Load (preload into RAM) a model, then refresh. */
  load: (name: string) => Promise<void>
  /** Unload a model from RAM, then refresh. */
  unload: (name: string) => Promise<void>
  /** Unload every loaded model, then refresh. */
  unloadEverything: () => Promise<void>
}

/**
 * Polls `GET /models` on an interval **only while `enabled`** (i.e. the panel
 * is open) and exposes load/unload actions. Never throws — an unreachable
 * backend simply reads as offline (`models === null`).
 */
export function useModels(enabled: boolean): UseModelsResult {
  const [models, setModels] = useState<ModelStatus[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [pending, setPending] = useState<Set<string>>(() => new Set())
  const isMountedRef = useRef(true)

  const refresh = useCallback(async (): Promise<void> => {
    const next = await getModels()
    if (!isMountedRef.current) return
    setModels(next)
    setIsLoading(false)
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    if (!enabled) return

    void refresh()
    const intervalId = setInterval(() => void refresh(), POLL_INTERVAL_MS)

    return () => {
      isMountedRef.current = false
      clearInterval(intervalId)
    }
  }, [enabled, refresh])

  const runAction = useCallback(
    async (name: string, action: () => Promise<unknown>): Promise<void> => {
      setPending((prev) => new Set(prev).add(name))
      try {
        await action()
        await refresh()
      } catch {
        // Backend offline / transient — a subsequent poll will reconcile state.
      } finally {
        if (isMountedRef.current) {
          setPending((prev) => {
            const next = new Set(prev)
            next.delete(name)
            return next
          })
        }
      }
    },
    [refresh],
  )

  const load = useCallback(
    (name: string) => runAction(name, () => loadModel(name)),
    [runAction],
  )

  const unload = useCallback(
    (name: string) => runAction(name, () => unloadModel(name)),
    [runAction],
  )

  const unloadEverything = useCallback(async (): Promise<void> => {
    try {
      await unloadAll()
      await refresh()
    } catch {
      // Offline / transient — the next poll reconciles.
    }
  }, [refresh])

  return {
    models,
    isLoading,
    isOnline: models !== null,
    pending,
    load,
    unload,
    unloadEverything,
  }
}
