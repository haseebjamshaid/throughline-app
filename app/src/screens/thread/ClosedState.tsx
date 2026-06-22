import { ArrowCounterClockwise } from '@phosphor-icons/react'
import { Button, Label } from '../../ui'
import { LoneTreeAtDawn } from '../../illustrations'

interface ClosedStateProps {
  /** Drop this thread and return to the resting page for a new one. */
  onNewThread: () => void
}

/**
 * The gentle closed loop — once the step is done, a lone tree at dawn and a calm
 * lowercase line. No fanfare, no streak: the loop's just closed. A quiet way back
 * to start a new thread whenever they're stuck again.
 */
export function ClosedState({ onNewThread }: ClosedStateProps) {
  return (
    <div className="flex flex-col items-center pb-16 pt-2 text-center">
      <LoneTreeAtDawn className="h-auto w-full max-w-[280px] opacity-95" aria-hidden />
      <Label tone="olive" className="mt-6">
        the loop's closed
      </Label>
      <h3 className="mt-3 max-w-md font-display text-[34px] font-medium lowercase leading-[1.1] tracking-[0.005em] text-ink">
        the loop's closed — come back when you're stuck again.
      </h3>
      <p className="mt-3 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
        nothing to keep going for. close the page; the thread will be here next
        time something tangles up.
      </p>
      <div className="mt-8">
        <Button variant="default" onClick={onNewThread}>
          <ArrowCounterClockwise weight="bold" aria-hidden className="h-4 w-4" />
          pull another thread
        </Button>
      </div>
    </div>
  )
}
