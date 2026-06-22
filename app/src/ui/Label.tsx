import type { ReactNode } from 'react'

/**
 * Tone roles map to the warm palette. The legacy `grey`/`orange`/`cream`
 * aliases are retained so existing callers keep working through the re-skin
 * (grey → muted taupe, orange → terracotta, cream → ink).
 */
type LabelTone =
  | 'soft'
  | 'terracotta'
  | 'clay'
  | 'olive'
  | 'ink'
  | 'grey'
  | 'orange'
  | 'cream'
  | 'cream-bright'

interface LabelProps {
  children: ReactNode
  /** Colour role for the label. Defaults to muted taupe. */
  tone?: LabelTone
  /** Render as a block (own line) instead of inline. */
  block?: boolean
  className?: string
}

const TONE_CLASS: Record<LabelTone, string> = {
  soft: 'text-ink-soft',
  terracotta: 'text-terracotta',
  clay: 'text-clay',
  olive: 'text-olive',
  ink: 'text-ink',
  // legacy aliases → warm equivalents
  grey: 'text-ink-soft',
  orange: 'text-terracotta',
  cream: 'text-ink',
  'cream-bright': 'text-ink',
}

/**
 * A small, lowercase Nunito Sans label — the quiet workhorse for metadata, nav,
 * section markers, and type tags. Warm humanist sans, modest letter-spacing,
 * small size, no decoration. Always lowercase.
 */
export function Label({ children, tone = 'soft', block, className = '' }: LabelProps) {
  return (
    <span
      className={`${block ? 'block' : 'inline-block'} font-label text-[11px] font-medium lowercase tracking-[0.04em] ${TONE_CLASS[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
