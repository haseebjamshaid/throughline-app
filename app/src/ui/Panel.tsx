import type { ReactNode } from 'react'

interface PanelProps {
  children: ReactNode
  /** Adds a gentle hover lift (a slightly stronger soft shadow). */
  interactive?: boolean
  /** Render as a semantic element other than <div> (e.g. 'article', 'li'). */
  as?: 'div' | 'article' | 'li' | 'section'
  className?: string
}

/**
 * The base plate: a warm raised `card` surface with a soft warm shadow, a soft
 * hairline border, and an organic 20px radius. Depth comes from the shadow and
 * the paper→card surface step — never hard borders. When `interactive`, hover
 * lifts it a touch with a stronger soft shadow.
 */
export function Panel({ children, interactive, as = 'div', className = '' }: PanelProps) {
  const Tag = as
  const interactiveClass = interactive
    ? 'transition-shadow duration-150 hover:shadow-lift'
    : ''
  return (
    <Tag
      className={`rounded-[20px] border border-border bg-card shadow-soft ${interactiveClass} ${className}`}
    >
      {children}
    </Tag>
  )
}
