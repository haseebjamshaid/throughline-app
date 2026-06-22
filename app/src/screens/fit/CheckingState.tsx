import { Label } from '../../ui'
import { LeafOnScale } from '../../illustrations'

/**
 * The calm waiting moment while the local model weighs the thing against your
 * profile. A slowly breathing leaf-on-scale and a quiet lowercase line — no
 * spinner urgency; the read takes a beat and that's fine.
 */
export function CheckingState() {
  return (
    <div
      className="flex flex-col items-center gap-5 py-20"
      role="status"
      aria-live="polite"
    >
      <LeafOnScale className="h-40 w-auto motion-safe:animate-pulse" />
      <div className="flex flex-col items-center gap-2">
        <Label tone="olive">weighing</Label>
        <p className="max-w-sm text-center font-body text-[18px] leading-[1.6] text-ink-soft">
          holding it up against everything you've kept…
        </p>
      </div>
    </div>
  )
}
