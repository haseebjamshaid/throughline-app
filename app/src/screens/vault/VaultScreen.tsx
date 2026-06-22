import { useMemo, useState } from 'react'
import { useVault } from '../../lib/appState'
import type { Item } from '../../lib/api'
import { VAULT_FILTERS } from '../../lib/itemMeta'
import { Label } from '../../ui'
import { Page } from '../Page'
import { OfflineNotice } from '../OfflineNotice'
import { ConnectPanel } from './ConnectPanel'
import { FilterRow } from './FilterRow'
import { ItemCard } from './ItemCard'
import { CaptureForm } from './CaptureForm'
import { IntakeControl } from './IntakeControl'

/** Apply the active filter pill to the item list (by type, or the `self` pseudo-filter). */
function filterItems(items: readonly Item[], activeKey: string): Item[] {
  const filter = VAULT_FILTERS.find((f) => f.key === activeKey)
  if (!filter || filter.types === null) return [...items]
  if (filter.key === 'self') return items.filter((it) => it.isSelf)
  const allowed = new Set(filter.types)
  return items.filter((it) => allowed.has(it.type))
}

/**
 * The vault screen — a warm curated library. When no vault is
 * connected it shows the elegant "point at your vault" panel (prefilled with
 * the sample vault). Once connected it shows a quiet count, the intake meter,
 * the "add to your shelf" capture panel, lowercase filter pills, and the
 * cover-plate item grid. The backend remembers the vault process-wide, so a
 * reload lands straight in the connected state.
 */
export function VaultScreen() {
  const {
    status,
    items,
    indexedCount,
    isConnecting,
    connectError,
    connect,
    capture,
    update,
    remove,
  } = useVault()
  const [activeFilter, setActiveFilter] = useState('all')

  const visible = useMemo(() => filterItems(items, activeFilter), [items, activeFilter])

  if (status === 'loading') {
    return (
      <Page title="vault" eyebrow="throughline">
        <Label tone="soft">reading the vault state…</Label>
      </Page>
    )
  }

  if (status === 'offline') {
    return (
      <Page title="vault" eyebrow="throughline">
        <OfflineNotice />
      </Page>
    )
  }

  if (status === 'disconnected') {
    return (
      <Page title="vault" eyebrow="throughline">
        <ConnectPanel
          isConnecting={isConnecting}
          error={connectError}
          onConnect={(path) => void connect(path)}
        />
      </Page>
    )
  }

  // Connected.
  const count = indexedCount !== null ? indexedCount : items.length
  const countLabel = `${count} ${count === 1 ? 'thing' : 'things'}`

  return (
    <Page
      title="vault"
      eyebrow="throughline"
      aside={<Label tone="soft">a library of {countLabel}</Label>}
    >
      <div className="flex flex-col gap-10">
        <IntakeControl />
        <CaptureForm onCapture={capture} />

        <section className="flex flex-col gap-6">
          <FilterRow activeKey={activeFilter} onChange={setActiveFilter} />

          {visible.length === 0 ? (
            <p className="font-body text-[18px] italic leading-[1.65] text-ink-soft">
              {items.length === 0
                ? 'nothing on the shelf yet. add something above to begin your library.'
                : 'nothing matches this filter.'}
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {visible.map((item, index) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  catalogNo={index + 1}
                  onSave={update}
                  onDelete={remove}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </Page>
  )
}
