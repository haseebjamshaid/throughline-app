import type { ReactNode } from 'react'
import { Label } from '../ui'
import { Page } from './Page'

interface PhasePlaceholderProps {
  title: string
  /** A quiet lowercase phase tag, e.g. "coming soon". */
  phase: string
  /** One serif line on what's coming. */
  promise: string
  /** Optional bespoke vignette illustration shown beside the promise. */
  vignette?: ReactNode
}

/**
 * An honest, gentle empty state for screens not yet written: a bespoke nature
 * vignette, a lowercase serif title, a quiet phase tag, and one EB Garamond line
 * on what's coming. No fake content, no spinner pretending to load.
 */
export function PhasePlaceholder({ title, phase, promise, vignette }: PhasePlaceholderProps) {
  return (
    <Page title={title} eyebrow="throughline">
      <div className="flex flex-col items-start gap-10 sm:flex-row sm:items-center">
        {vignette ? (
          <div className="w-full max-w-[260px] shrink-0 rounded-[20px] border border-border bg-card p-5 shadow-soft">
            {vignette}
          </div>
        ) : null}
        <div className="border-l-2 border-terracotta/40 pl-6">
          <Label tone="soft">{phase}</Label>
          <p className="mt-4 max-w-xl font-body text-[22px] italic leading-[1.55] text-ink">
            {promise}
          </p>
        </div>
      </div>
    </Page>
  )
}
