import { CloudSlash } from '@phosphor-icons/react'
import { Label, Panel } from '../ui'

/**
 * A gentle, lowercase "the machine is asleep" notice. Shown whenever the
 * backend is unreachable so a screen degrades to an instructive invitation
 * rather than a blank crash.
 */
export function OfflineNotice() {
  return (
    <Panel className="px-8 py-10">
      <span className="flex items-center gap-2">
        <CloudSlash aria-hidden className="h-4 w-4 text-ink-soft" />
        <Label tone="soft">backend · offline</Label>
      </span>
      <h3 className="mt-3 font-display text-[34px] font-medium lowercase leading-[1.05] tracking-[0.005em] text-ink">
        the machine is asleep
      </h3>
      <p className="mt-4 max-w-xl font-body text-[18px] leading-[1.65] text-ink">
        nothing is broken — the local engine just isn't running. start the
        server on{' '}
        <span className="font-medium text-clay">127.0.0.1:8000</span> and this
        page will wake up on its own.
      </p>
    </Panel>
  )
}
