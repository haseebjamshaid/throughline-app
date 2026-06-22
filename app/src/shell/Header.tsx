import { useLocation } from 'react-router-dom'
import { NAV_ITEMS, CAPTURE_ITEM } from '../nav'
import { StatusPill } from './StatusPill'
import { Label } from '../ui'
import { LayeredHills } from '../illustrations'

const ALL_ITEMS = [...NAV_ITEMS, CAPTURE_ITEM]

/**
 * Slim top bar with a faint layered-hills backdrop washing in from the right: a
 * quiet lowercase imprint line and the current section name in the display
 * serif (lowercase), with the backend status on the right (it still opens the
 * Models panel).
 */
export function Header() {
  const { pathname } = useLocation()
  const current = ALL_ITEMS.find((item) => item.path === pathname)

  return (
    <header className="relative flex h-20 shrink-0 items-center justify-between border-b border-border bg-card/40 px-8">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
        <LayeredHills className="absolute inset-y-0 right-0 h-full w-1/2 opacity-[0.14]" />
      </div>
      <div className="relative flex flex-col gap-1">
        <Label tone="soft">a field guide · throughline</Label>
        <h1 className="font-display text-2xl font-medium lowercase leading-none tracking-[0.005em] text-ink">
          {current?.label ?? ''}
        </h1>
      </div>
      <div className="relative">
        <StatusPill />
      </div>
    </header>
  )
}
