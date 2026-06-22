/** The four beats of the first-run walk, in order. */
export const STEP_LABELS = ['connect', 'read', 'portrait', 'the thread'] as const

interface StepperProps {
  /** Index of the active step (0–3). */
  current: number
}

/**
 * A quiet horizontal progress trail for the onboarding walk — four small dots
 * with lowercase labels. Past beats are olive, the current beat is clay and a
 * touch larger, and the rest sit muted. Decorative-but-orienting; aria-hidden
 * since the step headings carry the real structure.
 */
export function Stepper({ current }: StepperProps) {
  return (
    <ol className="flex items-center justify-center gap-2" aria-hidden>
      {STEP_LABELS.map((label, index) => {
        const isDone = index < current
        const isCurrent = index === current
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full transition-colors duration-300 ${
                isCurrent
                  ? 'scale-125 bg-clay'
                  : isDone
                    ? 'bg-olive'
                    : 'bg-border'
              }`}
            />
            <span
              className={`font-label text-[11px] font-medium lowercase tracking-[0.04em] transition-colors duration-300 ${
                isCurrent ? 'text-clay' : 'text-ink-soft'
              }`}
            >
              {label}
            </span>
            {index < STEP_LABELS.length - 1 ? (
              <span className="mx-1 h-px w-6 bg-border" />
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
