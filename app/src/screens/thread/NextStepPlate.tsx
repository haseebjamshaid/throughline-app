import { Check } from '@phosphor-icons/react'
import type { NextStep } from '../../lib/api'
import { Button, LitWindow } from '../../ui'

interface NextStepPlateProps {
  step: NextStep
  /** True while any thread request is in flight (disables the actions). */
  isBusy: boolean
  onDidIt: () => void
  onSmaller: () => void
  onDifferent: () => void
}

/**
 * The focal warm moment — the one next step on the glowing terracotta plate,
 * lifted above everything else. The step text reads in serif; beneath sit three
 * gentle actions: the decisive clay "did it ✓", a quieter "smaller", and a quiet
 * "different step". When the step is already the smaller variant, "smaller" is
 * disabled so the user isn't sent in circles.
 */
export function NextStepPlate({
  step,
  isBusy,
  onDidIt,
  onSmaller,
  onDifferent,
}: NextStepPlateProps) {
  const isAlreadySmaller = step.size === 'smaller'

  return (
    <LitWindow
      eyebrow="your one next step · today"
      className="w-full max-w-xl scale-[1.02] text-center shadow-lift"
    >
      <p className="font-body text-[24px] leading-[1.5] text-ink">{step.text}</p>

      <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
        <Button variant="primary" onClick={onDidIt} disabled={isBusy}>
          <Check weight="bold" aria-hidden className="h-4 w-4" />
          did it ✓
        </Button>
        <Button
          variant="default"
          onClick={onSmaller}
          disabled={isBusy || isAlreadySmaller}
          title={isAlreadySmaller ? 'already the smaller step' : undefined}
        >
          smaller
        </Button>
        <Button variant="default" onClick={onDifferent} disabled={isBusy}>
          different step
        </Button>
      </div>
    </LitWindow>
  )
}
