import { ArrowLineDown, ArrowLineUp } from '@phosphor-icons/react'
import { Label } from '../../ui'

/**
 * The inward/outward direction toggle. `inward` is active — ink text with a thin
 * terracotta tick beneath; `outward` is a quiet "later" note in V1, muted and
 * tagged, with a lowercase promise that nothing leaves this machine. Privacy as
 * a calm, structural statement.
 */
export function DirectionToggle() {
  return (
    <div className="flex flex-col gap-3">
      <Label tone="soft">direction</Label>
      <div className="flex items-center gap-6" role="group" aria-label="search direction">
        <span
          aria-current="true"
          className="relative flex items-center gap-1.5 pb-1 font-label text-[13px] font-semibold lowercase tracking-[0.03em] text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:rounded-full after:bg-terracotta"
        >
          <ArrowLineDown weight="bold" aria-hidden className="h-3.5 w-3.5 text-terracotta" />
          inward
        </span>
        <span
          aria-disabled="true"
          title="outward search arrives later"
          className="flex items-center gap-2 pb-1 font-label text-[13px] font-medium lowercase tracking-[0.03em] text-ink-soft"
        >
          <ArrowLineUp weight="bold" aria-hidden className="h-3.5 w-3.5" />
          outward
          <span className="rounded-full border border-border bg-sand/40 px-1.5 py-0.5 text-[10px] leading-none">
            later
          </span>
        </span>
      </div>
      <p className="font-body text-[15px] italic leading-[1.5] text-ink-soft">
        nothing leaves this machine.
      </p>
    </div>
  )
}
