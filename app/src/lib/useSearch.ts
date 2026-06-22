import { useCallback, useRef, useState } from 'react'
import { isApiStatus, search, type SearchInput, type SearchResult } from './api'

/** Coarse state of a vibe search. */
export type SearchState = 'idle' | 'searching' | 'done' | 'no-vault' | 'error'

export interface UseSearchResult {
  /** Lifecycle state the screen branches on. */
  state: SearchState
  /** Ranked results from the last completed search. */
  results: SearchResult[]
  /** The query that produced the current results (for the empty-result copy). */
  lastQuery: string
  /** Error message when `state === 'error'`, else `null`. */
  error: string | null
  /** Run a search; blank queries are ignored. */
  run: (input: SearchInput) => Promise<void>
}

/**
 * Owns a single feeling-search request lifecycle. Maps a 409 to a dedicated
 * `no-vault` state so the screen can invite the user to connect a vault first,
 * and never throws to the caller. A request id guards against out-of-order
 * responses when the user searches again quickly.
 */
export function useSearch(): UseSearchResult {
  const [state, setState] = useState<SearchState>('idle')
  const [results, setResults] = useState<SearchResult[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const requestIdRef = useRef(0)

  const run = useCallback(async (input: SearchInput): Promise<void> => {
    const query = input.query.trim()
    if (!query) return

    const requestId = ++requestIdRef.current
    setState('searching')
    setError(null)
    setLastQuery(query)

    try {
      const hits = await search({ ...input, query })
      if (requestId !== requestIdRef.current) return
      setResults(hits)
      setState('done')
    } catch (err: unknown) {
      if (requestId !== requestIdRef.current) return
      setResults([])
      if (isApiStatus(err, 409)) {
        setState('no-vault')
        return
      }
      if (isApiStatus(err, 0)) {
        setState('error')
        setError('the backend is offline — start it on 127.0.0.1:8000 and try again.')
        return
      }
      setState('error')
      setError(err instanceof Error ? err.message : 'search failed — try again.')
    }
  }, [])

  return { state, results, lastQuery, error, run }
}
