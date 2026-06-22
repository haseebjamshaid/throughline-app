import type { SearchResult } from '../../lib/api'

interface ResultRowProps {
  rank: number
  result: SearchResult
}

/**
 * One ranked search hit as a soft warm card: a quiet "no." numeral (oldstyle),
 * the title in Fraunces lowercase, a terracotta match% (the warm signal), and an
 * EB Garamond italic "why" line.
 */
export function ResultRow({ rank, result }: ResultRowProps) {
  const matchPercent = Math.round(result.score * 100)
  const no = `no. ${String(rank).padStart(3, '0')}`
  return (
    <article className="flex gap-5 rounded-[18px] border border-border bg-card p-5 shadow-soft transition-shadow duration-150 hover:shadow-lift">
      <span
        aria-hidden
        className="numerals-old w-14 shrink-0 pt-1 font-label text-[13px] font-semibold leading-none tracking-[0.02em] text-ink-soft"
      >
        {no}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h3 className="font-display text-[24px] font-medium lowercase leading-[1.1] tracking-[0.005em] text-ink">
            {result.title}
          </h3>
          <span className="numerals-old rounded-full bg-terracotta/15 px-2.5 py-0.5 font-label text-[12px] font-semibold lowercase tracking-[0.02em] text-clay">
            {matchPercent}% match
          </span>
        </div>
        {result.why ? (
          <p className="mt-2 font-body text-[16px] italic leading-[1.6] text-ink-soft">
            {result.why}
          </p>
        ) : null}
      </div>
    </article>
  )
}
