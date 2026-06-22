import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight } from '@phosphor-icons/react'
import { generateProfile, isApiStatus, type Profile } from '../lib/api'
import { Button, Label, Panel } from '../ui'
import { LoneTreeAtDawn } from '../illustrations'

interface RevealStepProps {
  /** Move on to the heart once the portrait has landed. */
  onContinue: () => void
}

// How many claims to surface in the first reveal — a taste, not the whole thing.
const PREVIEW_CLAIMS = 4

/** Translate a generate failure into a friendly, actionable lowercase message. */
function generateMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check ollama is running.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'the portrait could not be drawn — try again.'
}

/**
 * The third beat — the "that's me" moment. The library draws a first portrait
 * from the shelf (a slow model call) and reveals a taste of it: the palette and
 * a few backed claims. Honest about thinness via the profile's own confidence
 * note. Generation starts automatically on enter; failures offer a retry.
 */
export function RevealStep({ onContinue }: RevealStepProps) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const startedRef = useRef(false)

  const run = useCallback(async (): Promise<void> => {
    setError(null)
    setProfile(null)
    try {
      const next = await generateProfile()
      setProfile(next)
    } catch (err: unknown) {
      setError(generateMessage(err))
    }
  }, [])

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    void run()
  }, [run])

  if (error) {
    return (
      <div className="flex flex-col items-center text-center">
        <LoneTreeAtDawn aria-hidden className="h-32 w-auto opacity-70" />
        <h2 className="mt-4 max-w-lg font-display text-[34px] font-medium lowercase leading-[1.1] text-ink">
          the portrait slipped
        </h2>
        <p
          role="alert"
          className="mt-4 max-w-md font-body text-[17px] leading-[1.6] text-ink-soft"
        >
          {error}
        </p>
        <Button variant="primary" onClick={() => void run()} className="mt-6">
          try drawing it again
        </Button>
      </div>
    )
  }

  if (!profile) {
    return (
      <div
        className="flex flex-col items-center text-center"
        role="status"
        aria-live="polite"
      >
        <LoneTreeAtDawn aria-hidden className="h-36 w-auto motion-safe:animate-pulse" />
        <Label tone="olive" className="mt-4">
          drawing
        </Label>
        <h2 className="mt-2 max-w-lg font-display text-[38px] font-medium lowercase leading-[1.08] text-ink">
          drawing your portrait
        </h2>
        <p className="mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
          looking across everything at once for the threads that keep coming back…
        </p>
      </div>
    )
  }

  const claims = profile.claims.slice(0, PREVIEW_CLAIMS)

  return (
    <div className="flex flex-col items-center text-center">
      <Label tone="olive">your portrait</Label>
      <h2 className="mt-2 max-w-lg font-display text-[38px] font-medium lowercase leading-[1.08] tracking-[0.005em] text-ink">
        here's what i see
      </h2>
      <p className="mt-3 max-w-md font-body text-[16px] italic leading-[1.55] text-ink-soft">
        {profile.confidenceNote}
      </p>

      {profile.palette.length > 0 ? (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
          {profile.palette.map((swatch) => (
            <span
              key={swatch.hex}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card py-1 pl-1.5 pr-3 shadow-soft"
            >
              <span
                className="h-4 w-4 rounded-full border border-hairline"
                style={{ backgroundColor: swatch.hex }}
                aria-hidden
              />
              <span className="font-label text-[11px] font-medium lowercase tracking-[0.03em] text-ink-soft">
                {swatch.name}
              </span>
            </span>
          ))}
        </div>
      ) : null}

      {claims.length > 0 ? (
        <Panel className="mt-7 w-full max-w-lg px-7 py-6 text-left">
          <ul className="flex flex-col gap-4">
            {claims.map((claim) => (
              <li key={claim.id} className="flex flex-col gap-1">
                <Label tone="clay">{claim.section}</Label>
                <p className="font-body text-[18px] leading-[1.5] text-ink">
                  {claim.text}
                </p>
              </li>
            ))}
          </ul>
        </Panel>
      ) : (
        <p className="mt-6 max-w-md font-body text-[16px] leading-[1.6] text-ink-soft">
          too little to say much yet — add a few more notes and your portrait
          fills in.
        </p>
      )}

      <Button variant="primary" onClick={onContinue} className="mt-8">
        and now, the heart
        <ArrowRight weight="bold" aria-hidden className="h-4 w-4" />
      </Button>
    </div>
  )
}
