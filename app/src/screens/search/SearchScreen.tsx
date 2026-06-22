import { useState } from 'react'
import { useSearch } from '../../lib/appState'
import type { ItemType } from '../../lib/api'
import { SEARCH_FILTER_TYPES, TYPE_META } from '../../lib/itemMeta'
import { MagnifyingGlass } from '@phosphor-icons/react'
import { Button, Input, Label, Pill } from '../../ui'
import { HillsWithSun } from '../../illustrations'
import { Page } from '../Page'
import { DirectionToggle } from './DirectionToggle'
import { ResultRow } from './ResultRow'

/**
 * Vibe Search. Search the vault inward, by feeling. Renders the inward/outward
 * direction toggle, a feeling query input (amber focus), type-filter pills, and
 * a ranked result list. Empty/no-vault/offline states are instructive
 * invitations, never blank.
 */
export function SearchScreen() {
  const { state, results, lastQuery, error, run } = useSearch()
  const [query, setQuery] = useState('')
  const [activeTypes, setActiveTypes] = useState<ReadonlySet<ItemType>>(new Set())

  const toggleType = (type: ItemType): void => {
    setActiveTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    const types = activeTypes.size > 0 ? [...activeTypes] : undefined
    void run({ query: trimmed, inwardOnly: true, types, k: 12 })
  }

  return (
    <Page title="vibe search" eyebrow="throughline">
      <div className="flex flex-col gap-9">
        <DirectionToggle />

        <form onSubmit={submit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Input
                id="search-query"
                label="search your vault by feeling"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="warm and lonely…"
                autoComplete="off"
              />
            </div>
            <Button
              type="submit"
              variant="primary"
              disabled={state === 'searching' || !query.trim()}
            >
              <MagnifyingGlass weight="bold" aria-hidden className="h-4 w-4" />
              {state === 'searching' ? 'searching' : 'search'}
            </Button>
          </div>

          <div className="flex flex-col gap-2">
            <Label tone="grey">filter by type</Label>
            <div className="flex flex-wrap gap-3" role="group" aria-label="filter by type">
              {SEARCH_FILTER_TYPES.map((type) => (
                <Pill
                  key={type}
                  active={activeTypes.has(type)}
                  onClick={() => toggleType(type)}
                >
                  {TYPE_META[type].short}
                </Pill>
              ))}
            </div>
          </div>
        </form>

        <SearchBody
          state={state}
          results={results}
          lastQuery={lastQuery}
          error={error}
        />
      </div>
    </Page>
  )
}

interface SearchBodyProps {
  state: ReturnType<typeof useSearch>['state']
  results: ReturnType<typeof useSearch>['results']
  lastQuery: string
  error: string | null
}

/** Branch the result region on the search lifecycle state. */
function SearchBody({ state, results, lastQuery, error }: SearchBodyProps) {
  if (state === 'idle') {
    return (
      <EmptyVignette>
        <Invitation>
          try a feeling — <span className="text-ink">"warm and lonely"</span>.
        </Invitation>
      </EmptyVignette>
    )
  }

  if (state === 'searching') {
    return <Label tone="soft">searching your vault…</Label>
  }

  if (state === 'no-vault') {
    return (
      <div className="border-l-2 border-terracotta/40 pl-4">
        <Label tone="soft">no vault yet</Label>
        <p className="mt-2 font-body text-[18px] leading-[1.65] text-ink">
          connect a vault first — open the vault page and point the machine at
          your notes.
        </p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="border-l-2 border-clay pl-4">
        <Label tone="soft">search didn't land</Label>
        <p className="mt-2 font-body text-[18px] leading-[1.65] text-ink">
          {error ?? 'something went wrong — try again.'}
        </p>
      </div>
    )
  }

  // done
  if (results.length === 0) {
    return (
      <EmptyVignette>
        <Invitation>
          nothing answered to <span className="text-ink">"{lastQuery}"</span>. try
          another feeling.
        </Invitation>
      </EmptyVignette>
    )
  }

  return (
    <section className="flex flex-col">
      <Label tone="soft" block>
        {results.length} {results.length === 1 ? 'echo' : 'echoes'} for "{lastQuery}"
      </Label>
      <div className="mt-3 flex flex-col gap-3">
        {results.map((result, index) => (
          <ResultRow key={result.itemId} rank={index + 1} result={result} />
        ))}
      </div>
    </section>
  )
}

/** Centers a bespoke hills vignette above a serif invitation line. */
function EmptyVignette({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-6 py-6 text-center">
      <HillsWithSun className="h-auto w-full max-w-[280px] opacity-90" />
      {children}
    </div>
  )
}

/** A serif, lowercase, second-person empty-state invitation. */
function Invitation({ children }: { children: React.ReactNode }) {
  return (
    <p className="max-w-md font-body text-[24px] italic leading-[1.45] text-ink-soft">
      {children}
    </p>
  )
}
