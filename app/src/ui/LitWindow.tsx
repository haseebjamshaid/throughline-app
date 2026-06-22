import type { ReactNode } from 'react'
import { Sun } from '@phosphor-icons/react'

interface LitWindowProps {
  children: ReactNode
  /** Lowercase eyebrow label (e.g. "your one next step · today"). */
  eyebrow?: string
  className?: string
}

/**
 * The one warm thing — a softly glowing terracotta plate with a small gold sun,
 * the single focal moment in the library. Reserved for the Thread's "next step"
 * plate. Warm fill, rounded, soft shadow.
 */
export function LitWindow({ children, eyebrow, className = '' }: LitWindowProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-[20px] border border-terracotta/40 bg-terracotta/[0.12] px-8 py-9 shadow-soft ${className}`}
    >
      {/* a soft low sun, warming the plate from above */}
      <Sun
        weight="fill"
        aria-hidden
        className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 text-gold/40"
      />
      {eyebrow ? (
        <span className="mb-4 flex items-center justify-center gap-2 font-label text-[11px] font-semibold lowercase tracking-[0.06em] text-clay">
          <Sun weight="fill" aria-hidden className="h-3.5 w-3.5" />
          {eyebrow}
        </span>
      ) : null}
      <div className="relative">{children}</div>
    </div>
  )
}
