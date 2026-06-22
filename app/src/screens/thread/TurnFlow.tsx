import type { ThreadTurn } from '../../lib/api'
import { Label } from '../../ui'
import { ConnectionCard } from './ConnectionCard'
import { NextStepPlate } from './NextStepPlate'

interface TurnFlowProps {
  turn: ThreadTurn
  /** True while a follow-up request is in flight (disables the plate actions). */
  isBusy: boolean
  /** Any unexpected error message from a follow-up, or `null`. */
  error: string | null
  onDidIt: () => void
  onSmaller: () => void
  onDifferent: () => void
  /** Drop the current thread and start a new one. */
  onNewThread: () => void
}

/**
 * The quiet vertical flow of one thread turn: the stuck statement as a soft
 * right-aligned bubble, then one question as a left bubble, then the connection
 * the library found from the user's own shelf (omitted gracefully when none),
 * and finally — set apart as the clear focal point — the one next step plate.
 */
export function TurnFlow({
  turn,
  isBusy,
  error,
  onDidIt,
  onSmaller,
  onDifferent,
  onNewThread,
}: TurnFlowProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-7 pb-16">
      {/* 1 · the user's stuck statement — a soft right-aligned bubble */}
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-[18px] rounded-tr-md border border-border bg-paper-dim px-5 py-3.5 shadow-soft">
          <Label tone="soft" className="mb-1 block text-right">
            you said
          </Label>
          <p className="font-body text-[18px] leading-[1.6] text-ink">{turn.stuck}</p>
        </div>
      </div>

      {/* 2 · one question — a left bubble, the question in calm serif */}
      {turn.question ? (
        <div className="flex justify-start">
          <div className="max-w-[85%] rounded-[18px] rounded-tl-md border border-border bg-card px-5 py-4 shadow-soft">
            <Label tone="olive" className="mb-1.5 block">
              one question
            </Label>
            <p className="font-display text-[22px] font-medium lowercase leading-[1.35] tracking-[0.005em] text-ink">
              {turn.question}
            </p>
          </div>
        </div>
      ) : null}

      {/* 3 · a thread i found — the connection from their own shelf (optional) */}
      {turn.connection ? <ConnectionCard connection={turn.connection} /> : null}

      {error ? (
        <p
          role="alert"
          className="rounded-[14px] border-l-2 border-clay bg-clay/8 py-3 pl-4 pr-4 font-body text-[16px] leading-[1.6] text-ink"
        >
          {error}
        </p>
      ) : null}

      {/* 4 · the next step — the focal warm plate, set apart and centred */}
      <div className="mt-3 flex flex-col items-center gap-5">
        <NextStepPlate
          step={turn.nextStep}
          isBusy={isBusy}
          onDidIt={onDidIt}
          onSmaller={onSmaller}
          onDifferent={onDifferent}
        />
        <button
          type="button"
          onClick={onNewThread}
          disabled={isBusy}
          className="font-label text-[13px] font-medium lowercase tracking-[0.03em] text-ink-soft underline decoration-border underline-offset-4 transition-colors duration-150 hover:text-ink hover:decoration-terracotta/50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          start a different thread
        </button>
      </div>
    </div>
  )
}
