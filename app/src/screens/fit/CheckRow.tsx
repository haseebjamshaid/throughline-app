import { Check, Path } from '@phosphor-icons/react'
import type { FitCheckItem } from '../../lib/api'

interface CheckRowProps {
  check: FitCheckItem
  /** Push back on a drifting check ("that's me on purpose"). */
  onDisagree: (rule: string) => void
}

/**
 * One line of the fit checklist, tied to a real profile claim. A pass shows a
 * soft olive check; a drift shows a clay path-mark (honest distance, never a red
 * error) with its concrete fix and a quiet "that's me on purpose" pushback that
 * hides + remembers the rule. The rule text reads in serif — it's the user's own
 * claim, in their own voice.
 */
export function CheckRow({ check, onDisagree }: CheckRowProps) {
  return (
    <li className="flex items-start gap-3 py-3">
      <span
        aria-hidden
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
          check.passed ? 'bg-olive/15 text-olive' : 'bg-clay/12 text-clay'
        }`}
      >
        {check.passed ? (
          <Check weight="bold" className="h-3.5 w-3.5" />
        ) : (
          <Path weight="bold" className="h-3.5 w-3.5" />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <p className="font-body text-[17px] leading-[1.5] text-ink">{check.rule}</p>

        {!check.passed && check.fix ? (
          <p className="mt-1 font-body text-[15px] italic leading-[1.55] text-ink-soft">
            to bring it closer: {check.fix}
          </p>
        ) : null}

        {!check.passed ? (
          <button
            type="button"
            onClick={() => onDisagree(check.rule)}
            className="mt-2 font-label text-[12px] font-medium lowercase tracking-[0.02em] text-olive underline decoration-olive/30 underline-offset-2 transition-colors duration-150 hover:decoration-olive"
          >
            that's me on purpose
          </button>
        ) : null}
      </div>
    </li>
  )
}
