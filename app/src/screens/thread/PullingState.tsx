import { Label } from '../../ui'
import { WindingPath } from '../../illustrations'

/**
 * The calm loading moment while the library works — the winding path and a quiet
 * lowercase line, gently breathing. Not a harsh spinner; the wait is part of the
 * stillness.
 */
export function PullingState() {
  return (
    <div
      className="flex flex-col items-center pb-16 pt-2"
      role="status"
      aria-live="polite"
    >
      <WindingPath className="h-44 w-auto animate-pulse [animation-duration:2.4s]" />
      <Label tone="olive" className="mt-4">
        pulling a thread…
      </Label>
      <p className="mt-3 max-w-md text-center font-body text-[18px] italic leading-[1.65] text-ink-soft">
        reading back through what you've kept — this can take a moment.
      </p>
    </div>
  )
}
