import { ArrowRight } from '@phosphor-icons/react'
import { Button, Label } from '../ui'
import { WindingPath } from '../illustrations'

interface HandoffStepProps {
  /** Finish onboarding and land in the thread (the heart). */
  onPullThread: () => void
  /** Finish onboarding and let the user roam the app on their own. */
  onExplore: () => void
}

/**
 * The last beat — the handoff to the heart. The portrait is drawn; now the
 * thread is what throughline is really for. A warm winding path toward the light
 * and one clear invitation to pull a first thread, with a quiet "i'll explore"
 * for anyone who'd rather wander first.
 */
export function HandoffStep({ onPullThread, onExplore }: HandoffStepProps) {
  return (
    <div className="flex flex-col items-center text-center">
      <WindingPath aria-hidden className="h-40 w-auto" />
      <Label tone="olive" className="mt-3">
        the heart
      </Label>
      <h2 className="mt-2 max-w-lg font-display text-[38px] font-medium lowercase leading-[1.08] tracking-[0.005em] text-ink">
        you're set — now the thread
      </h2>
      <p className="mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
        whenever you're stuck, say it in plain words. i'll pull one question, one
        connection from your own shelf, and one small next step you can do today.
        that's the whole point of this place.
      </p>

      <div className="mt-8 flex flex-col items-center gap-3">
        <Button variant="primary" onClick={onPullThread}>
          pull my first thread
          <ArrowRight weight="bold" aria-hidden className="h-4 w-4" />
        </Button>
        <button
          type="button"
          onClick={onExplore}
          className="font-label text-[13px] font-medium lowercase tracking-[0.02em] text-ink-soft underline decoration-border underline-offset-2 transition-colors duration-150 hover:text-clay hover:decoration-terracotta"
        >
          i'll explore on my own
        </button>
      </div>
    </div>
  )
}
