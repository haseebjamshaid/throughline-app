/** The three honest fit bands — warm, never harsh (no green/red judgment). */
export type FitBand = 'high' | 'mid' | 'low'

interface ScoreDialProps {
  /** Closeness to the centre of your taste, 0–100. */
  score: number
}

/** Map a 0–100 score to its honest band. */
export function scoreBand(score: number): FitBand {
  if (score >= 67) return 'high'
  if (score >= 34) return 'mid'
  return 'low'
}

// Geometry for the donut arc. r chosen so the 120-box leaves room for the stroke.
const R = 52
const CIRCUMFERENCE = 2 * Math.PI * R

// Each band paints in a warm earth tone — olive (very you), terracotta (mostly),
// clay (drifting) — so the dial reads as honest distance, not pass/fail.
const BAND_STROKE: Record<FitBand, string> = {
  high: 'var(--color-olive)',
  mid: 'var(--color-terracotta)',
  low: 'var(--color-clay)',
}

/**
 * The focal warm moment of fit check — a softly filling donut dial with the
 * 0–100 closeness in big lowercase serif at its centre, ringed in the band's
 * earth tone. The arc grows clockwise from the top. Decorative; the number and
 * verdict carry the meaning, so it is aria-hidden with the score announced in
 * the surrounding copy.
 */
export function ScoreDial({ score }: ScoreDialProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)))
  const band = scoreBand(clamped)
  const dashoffset = CIRCUMFERENCE * (1 - clamped / 100)

  return (
    <div className="relative h-40 w-40 shrink-0" aria-hidden>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        {/* faint sand track */}
        <circle
          cx="60"
          cy="60"
          r={R}
          fill="none"
          stroke="var(--color-sand)"
          strokeOpacity="0.6"
          strokeWidth="10"
        />
        {/* the warm filling arc */}
        <circle
          cx="60"
          cy="60"
          r={R}
          fill="none"
          stroke={BAND_STROKE[band]}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashoffset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-[44px] font-medium leading-none text-ink">
          {clamped}
        </span>
        <span className="mt-1 font-label text-[11px] font-medium lowercase tracking-[0.06em] text-ink-soft">
          how you · / 100
        </span>
      </div>
    </div>
  )
}
