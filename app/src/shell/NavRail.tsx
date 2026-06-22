import { NavLink } from 'react-router-dom'
import type { Icon } from '@phosphor-icons/react'
import {
  BookOpen,
  Leaf,
  Path,
  Scales,
  MagnifyingGlass,
  PlusCircle,
} from '@phosphor-icons/react'
import { NAV_ITEMS, CAPTURE_ITEM } from '../nav'
import { ThroughlineMark } from '../illustrations'

/**
 * Left vertical rail, warm on paper. The wordmark `throughline` (Fraunces,
 * lowercase) carries the ThroughlineMark roundel as its emblem. Primary nav
 * items pair a nature-appropriate Phosphor icon with a lowercase Nunito label;
 * the active item gets a terracotta tick, a filled icon, and a soft warm wash.
 * `add to your shelf` is pinned to the bottom as a soft outline plate.
 */

/** Phosphor icon per nav path. Nature-appropriate, consistent weight. */
const NAV_ICON: Record<string, Icon> = {
  '/vault': BookOpen,
  '/profile': Leaf,
  '/thread': Path,
  '/fit-check': Scales,
  '/vibe-search': MagnifyingGlass,
}

export function NavRail() {
  return (
    <nav className="flex w-60 shrink-0 flex-col border-r border-border bg-card/60 py-8">
      <div className="flex items-center gap-2.5 px-6 pb-12">
        <ThroughlineMark className="h-8 w-8 shrink-0" />
        <span className="font-display text-[26px] font-medium lowercase leading-none tracking-[0.005em] text-ink">
          throughline
        </span>
      </div>

      <ul className="flex flex-1 flex-col gap-0.5 px-3">
        {NAV_ITEMS.map((item) => {
          const IconCmp = NAV_ICON[item.path] ?? Leaf
          return (
            <li key={item.path}>
              <NavLink to={item.path} className={navLinkClass}>
                {({ isActive }) => (
                  <>
                    <span
                      aria-hidden
                      className={`absolute left-0 top-1/2 h-5 -translate-y-1/2 w-[3px] rounded-full ${isActive ? 'bg-terracotta' : 'bg-transparent'}`}
                    />
                    <IconCmp
                      weight={isActive ? 'fill' : 'regular'}
                      aria-hidden
                      className={`h-5 w-5 shrink-0 ${isActive ? 'text-terracotta' : 'text-ink-soft'}`}
                    />
                    {item.label}
                  </>
                )}
              </NavLink>
            </li>
          )
        })}
      </ul>

      <div className="mt-6 px-5 pt-2">
        <NavLink to={CAPTURE_ITEM.path} className={captureClass}>
          <PlusCircle weight="duotone" aria-hidden className="h-5 w-5 shrink-0" />
          {CAPTURE_ITEM.label}
        </NavLink>
      </div>
    </nav>
  )
}

const BASE_LINK =
  'relative flex items-center gap-3 rounded-[12px] px-3 py-2.5 font-label text-[13px] font-medium lowercase tracking-[0.03em] transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 focus-visible:ring-inset'

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return isActive
    ? `${BASE_LINK} bg-terracotta/12 text-ink`
    : `${BASE_LINK} text-ink-soft hover:bg-sand/40 hover:text-ink`
}

function captureClass({ isActive }: { isActive: boolean }): string {
  const base =
    'flex items-center justify-center gap-2 rounded-full border px-3 py-2.5 font-label text-[13px] font-semibold lowercase tracking-[0.03em] transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50'
  return isActive
    ? `${base} border-clay bg-clay text-card shadow-soft`
    : `${base} border-border bg-card text-clay shadow-soft hover:-translate-y-px hover:shadow-lift`
}
