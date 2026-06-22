import type { ReactNode } from 'react'

interface PillProps {
  children: ReactNode
  /** Active filter: soft terracotta fill + ink text. Inactive: muted, warms on hover. */
  active?: boolean
  disabled?: boolean
  onClick?: () => void
  /** Optional title for tooltip / a11y. */
  title?: string
}

/**
 * A lowercase, fully-rounded filter pill. Active is a soft terracotta wash with
 * a warm border and ink text; inactive is a quiet sand-tinted chip that warms on
 * hover. Gentle, never shouty.
 */
export function Pill({ children, active, disabled, onClick, title }: PillProps) {
  const stateClass = active
    ? 'border-terracotta/50 bg-terracotta/15 text-ink'
    : 'border-transparent bg-sand/40 text-ink-soft hover:bg-sand/70 hover:text-ink'
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={active}
      className={`rounded-full border px-3.5 py-1.5 font-label text-[12px] font-medium lowercase tracking-[0.03em] transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 disabled:cursor-not-allowed disabled:opacity-40 ${stateClass}`}
    >
      {children}
    </button>
  )
}
