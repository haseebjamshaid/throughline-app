import { useCallback, useEffect, useRef, useState } from 'react'
import {
  captureItem,
  connectVault,
  deleteItem,
  getItems,
  isApiStatus,
  updateItem,
  type CaptureInput,
  type Item,
  type ItemPatch,
} from './api'

/** Connection state of the vault, derived from the items fetch + connect calls. */
export type VaultStatus = 'loading' | 'offline' | 'disconnected' | 'connected'

export interface UseVaultResult {
  /** Coarse connection state the screen branches on. */
  status: VaultStatus
  /** Loaded items (newest first). Empty until a vault is connected. */
  items: Item[]
  /** Indexed count from the most recent successful connect, if any. */
  indexedCount: number | null
  /** True while a connect request is in flight. */
  isConnecting: boolean
  /** Last connect error message, or `null`. */
  connectError: string | null
  /** Connect (and index) a vault by absolute path. */
  connect: (path: string) => Promise<void>
  /** Capture a new item and prepend it to the list. Throws on failure. */
  capture: (input: CaptureInput) => Promise<Item>
  /** Edit an item (metadata and/or body); reconciles the list. Throws on failure. */
  update: (id: string, patch: ItemPatch) => Promise<void>
  /** Delete an item and drop it from the list. Throws on failure. */
  remove: (id: string) => Promise<void>
  /** Re-fetch the item list. */
  refresh: () => Promise<void>
}

/**
 * Owns the connected-vault lifecycle: it probes `GET /vault/items` once on
 * mount to learn whether a vault is already connected (the backend remembers
 * one process-wide), exposes a `connect` action, and keeps the item list in
 * sync after captures. Never throws on read — an unreachable backend reads as
 * `offline`.
 */
export function useVault(): UseVaultResult {
  const [status, setStatus] = useState<VaultStatus>('loading')
  const [items, setItems] = useState<Item[]>([])
  const [indexedCount, setIndexedCount] = useState<number | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectError, setConnectError] = useState<string | null>(null)
  const isMountedRef = useRef(true)

  const refresh = useCallback(async (): Promise<void> => {
    const next = await getItems()
    if (!isMountedRef.current) return
    if (next === null) {
      setStatus('offline')
      return
    }
    setItems(next)
    // A reachable backend with zero items most likely means "no vault yet".
    setStatus((prev) => (prev === 'connected' || next.length > 0 ? 'connected' : 'disconnected'))
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    // Probe once on mount via a local async wrapper. State updates only happen
    // after the awaited fetch resolves (a microtask), never synchronously.
    const probe = async (): Promise<void> => {
      await refresh()
    }
    void probe()
    return () => {
      isMountedRef.current = false
    }
  }, [refresh])

  const connect = useCallback(async (path: string): Promise<void> => {
    setIsConnecting(true)
    setConnectError(null)
    try {
      const connection = await connectVault(path)
      if (!isMountedRef.current) return
      setIndexedCount(connection.indexed)
      setStatus('connected')
      const next = await getItems()
      if (!isMountedRef.current) return
      setItems(next ?? [])
    } catch (error: unknown) {
      if (!isMountedRef.current) return
      setConnectError(connectErrorMessage(error))
    } finally {
      if (isMountedRef.current) setIsConnecting(false)
    }
  }, [])

  const capture = useCallback(async (input: CaptureInput): Promise<Item> => {
    const created = await captureItem(input)
    if (isMountedRef.current) {
      setItems((prev) => [created, ...prev.filter((it) => it.id !== created.id)])
      setStatus('connected')
    }
    return created
  }, [])

  const update = useCallback(async (id: string, patch: ItemPatch): Promise<void> => {
    const updated = await updateItem(id, patch)
    if (isMountedRef.current) {
      setItems((prev) => prev.map((it) => (it.id === id ? updated : it)))
    }
  }, [])

  const remove = useCallback(async (id: string): Promise<void> => {
    await deleteItem(id)
    if (isMountedRef.current) {
      setItems((prev) => prev.filter((it) => it.id !== id))
    }
  }, [])

  return {
    status,
    items,
    indexedCount,
    isConnecting,
    connectError,
    connect,
    capture,
    update,
    remove,
    refresh,
  }
}

/** Translate a connect failure into a friendly, actionable message. */
function connectErrorMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check Ollama is running.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'could not connect to that vault — check the path and try again.'
}
