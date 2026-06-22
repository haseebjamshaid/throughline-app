interface MeterProps {
  /** Completed units. */
  value: number
  /** Total units. */
  max: number
  /** Accessible label for the progressbar. */
  ariaLabel?: string
}

/**
 * A soft terracotta line that fills left-to-right over a faint sand track —
 * gentle and warm, lightly rounded. Used by the vault intake reader.
 */
export function Meter({ value, max, ariaLabel }: MeterProps) {
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0
  const percent = Math.round(ratio * 100)
  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-label={ariaLabel}
      className="h-1.5 w-full overflow-hidden rounded-full bg-sand/60"
    >
      <div
        aria-hidden
        className="h-full rounded-full bg-terracotta transition-[width] duration-300"
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}
