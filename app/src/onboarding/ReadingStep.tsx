import { useEffect, useRef } from 'react'
import { ArrowRight } from '@phosphor-icons/react'
import { useIntake } from '../lib/useIntake'
import { Button, Label, Meter } from '../ui'
import { PineRidge } from '../illustrations'

interface ReadingStepProps {
  /** Items indexed at connect time — used to set honest expectations. */
  indexed: number | null
  /** Continue to the portrait (with however much has been read so far). */
  onContinue: () => void
}

// Below this many items the first read is honestly "thin".
const THIN_THRESHOLD = 6

/**
 * The second beat — the library reads your shelf, one thing at a time, with a
 * live count and the title it's on. Reading enriches the portrait but isn't
 * required to finish: "continue" is always available, and an empty/thin shelf is
 * named honestly rather than hidden. Starts automatically on enter.
 */
export function ReadingStep({ indexed, onContinue }: ReadingStepProps) {
  const { state, progress, error, start } = useIntake()
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    void start()
  }, [start])

  const total = progress?.total ?? indexed ?? 0
  const done = progress?.done ?? 0
  const isEmpty = (progress !== null && progress.total === 0) || indexed === 0
  const isDone = state === 'done' || isEmpty
  const isThin = total > 0 && total < THIN_THRESHOLD

  return (
    <div className="flex flex-col items-center text-center">
      <PineRidge aria-hidden className="h-32 w-auto" />
      <Label tone="olive" className="mt-4">
        {isDone ? 'read' : 'reading'}
      </Label>
      <h2 className="mt-2 max-w-lg font-display text-[38px] font-medium lowercase leading-[1.08] tracking-[0.005em] text-ink">
        {isEmpty ? 'an empty shelf, for now' : 'reading your shelf'}
      </h2>

      {isEmpty ? (
        <p className="mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
          nothing to read here yet — that's ok. you can add notes any time and i'll
          keep reading. for now, let's sketch a first, honest portrait from what
          little there is.
        </p>
      ) : (
        <>
          <p className="mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
            i'm reading each thing in place — what it's about, how it feels, the
            threads between them. this is the part that takes a breath.
          </p>

          <div className="mt-8 w-full max-w-md">
            <Meter value={done} max={total || 1} ariaLabel="reading progress" />
            <p className="mt-3 font-label text-[13px] font-medium lowercase tracking-[0.03em] text-ink-soft numerals-old">
              {isDone ? `read ${total} of ${total}` : `reading ${done} of ${total}`}
              {progress?.currentTitle && !isDone ? (
                <span className="text-clay"> · {progress.currentTitle}</span>
              ) : null}
            </p>
          </div>
        </>
      )}

      {isThin && !isEmpty ? (
        <p className="mt-5 max-w-md rounded-[12px] border-l-2 border-gold/50 bg-gold/10 py-2.5 pl-3.5 pr-3.5 text-left font-body text-[15px] leading-[1.55] text-ink">
          a small shelf makes a thin first read — feed it more over time and the
          portrait sharpens.
        </p>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="mt-5 max-w-md rounded-[12px] border-l-2 border-clay bg-clay/8 py-2.5 pl-3.5 pr-3.5 font-body text-[15px] leading-[1.55] text-ink"
        >
          {error}
        </p>
      ) : null}

      <div className="mt-8 flex flex-col items-center gap-3">
        <Button variant="primary" onClick={onContinue}>
          {isDone ? 'sketch my portrait' : 'continue with what you have'}
          <ArrowRight weight="bold" aria-hidden className="h-4 w-4" />
        </Button>
        {!isDone && !isEmpty ? (
          <span className="font-body text-[14px] italic text-ink-soft">
            you can keep reading in the background — it picks up where it left off.
          </span>
        ) : null}
      </div>
    </div>
  )
}
