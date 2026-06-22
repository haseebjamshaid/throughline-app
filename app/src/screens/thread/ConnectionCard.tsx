import type { ThreadConnection } from '../../lib/api'
import { Label } from '../../ui'
import { Sprig } from '../../illustrations'

interface ConnectionCardProps {
  connection: ThreadConnection
}

/**
 * "a thread i found" — a visually distinct card carrying a line pulled from the
 * user's own shelf. A warm gold/terracotta-washed plate with a small sprig, the
 * quoted line in serif italic (their own words), the reason it connects, and the
 * source title. Quietly special — proof the step came from their own library.
 */
export function ConnectionCard({ connection }: ConnectionCardProps) {
  return (
    <article className="relative overflow-hidden rounded-[18px] border border-gold/40 bg-gold/[0.1] px-6 py-5 shadow-soft">
      <Sprig
        aria-hidden
        className="pointer-events-none absolute -right-2 -top-2 h-12 w-12 opacity-30"
      />
      <span className="relative flex items-center gap-1.5">
        <Sprig aria-hidden className="h-3.5 w-3.5" />
        <Label tone="clay">a thread i found</Label>
      </span>

      <blockquote className="relative mt-3 border-l-2 border-terracotta/40 pl-4 font-body text-[20px] italic leading-[1.5] text-ink">
        “{connection.quote}”
      </blockquote>

      {connection.why ? (
        <p className="relative mt-3 font-body text-[16px] leading-[1.6] text-ink-soft">
          {connection.why}
        </p>
      ) : null}

      {connection.title ? (
        <p className="relative mt-3 font-label text-[12px] font-medium lowercase tracking-[0.03em] text-ink-soft">
          from your shelf · <span className="text-clay">{connection.title}</span>
        </p>
      ) : null}
    </article>
  )
}
