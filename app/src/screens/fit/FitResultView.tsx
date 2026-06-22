import { ArrowCounterClockwise } from '@phosphor-icons/react'
import type { FitResult } from '../../lib/api'
import { Button, Label, LitWindow, Panel } from '../../ui'
import { Sprig } from '../../illustrations'
import { CheckRow } from './CheckRow'
import { ScoreDial } from './ScoreDial'

interface FitResultViewProps {
  result: FitResult
  /** Push back on a drifting check. */
  onDisagree: (rule: string) => void
  /** Clear the result and hold something else up. */
  onReset: () => void
}

/**
 * The fit result, read top to bottom: the focal score dial + honest verdict on
 * a warm glowing plate, then the checklist of what fits and what drifts (each
 * tied to a real profile claim, each driftable to "that's me on purpose"), then
 * the closest things from the user's own shelf, and a quiet "weigh another".
 */
export function FitResultView({ result, onDisagree, onReset }: FitResultViewProps) {
  const fits = result.checks.filter((c) => c.passed)
  const drifts = result.checks.filter((c) => !c.passed)

  return (
    <div className="flex flex-col items-center gap-8 pb-16">
      <LitWindow eyebrow="the read" className="w-full max-w-xl shadow-lift">
        <div className="flex flex-col items-center gap-5 text-center sm:flex-row sm:items-center sm:gap-7 sm:text-left">
          <ScoreDial score={result.score} />
          <p className="font-body text-[22px] leading-[1.5] text-ink">
            {result.verdict}
          </p>
        </div>
      </LitWindow>

      {result.checks.length > 0 ? (
        <Panel className="w-full max-w-xl px-6 py-5">
          <span className="flex items-center gap-1.5">
            <Sprig aria-hidden className="h-3.5 w-3.5" />
            <Label tone="clay">what fits · what drifts</Label>
          </span>
          <ul className="mt-2 divide-y divide-border/60">
            {[...drifts, ...fits].map((check) => (
              <CheckRow key={check.rule} check={check} onDisagree={onDisagree} />
            ))}
          </ul>
        </Panel>
      ) : (
        <p className="max-w-md text-center font-body text-[16px] leading-[1.6] text-ink-soft">
          no firm claims to check against yet — feed your shelf a little more and
          the read sharpens.
        </p>
      )}

      {result.closest.length > 0 ? (
        <div className="w-full max-w-xl">
          <span className="flex items-center justify-center gap-1.5 sm:justify-start">
            <Label tone="soft">closest on your shelf</Label>
          </span>
          <ul className="mt-3 flex flex-wrap justify-center gap-2 sm:justify-start">
            {result.closest.map((item) => (
              <li
                key={item.itemId}
                className="inline-flex items-baseline gap-2 rounded-full border border-border bg-card px-3.5 py-1.5 shadow-soft"
              >
                <span className="font-body text-[15px] text-ink">{item.title}</span>
                <span className="font-label text-[11px] font-medium tracking-[0.03em] text-clay numerals-old">
                  {item.score}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Button variant="default" onClick={onReset}>
        <ArrowCounterClockwise weight="bold" aria-hidden className="h-4 w-4" />
        weigh another
      </Button>
    </div>
  )
}
