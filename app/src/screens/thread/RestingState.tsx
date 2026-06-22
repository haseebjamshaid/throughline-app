import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from '@phosphor-icons/react'
import { Button, Label, Textarea } from '../../ui'
import { WindingPath } from '../../illustrations'

interface RestingStateProps {
  /** Pull a thread from the stuck statement. */
  onPull: (stuck: string) => void
  /** True while a pull is in flight (disables the input + submit). */
  isBusy: boolean
  /** Set when the last pull failed because no vault is connected (409). */
  noVault: boolean
  /** Any unexpected error message, or `null`. */
  error: string | null
}

/**
 * The calm resting page — a faint winding path descending toward the light and a
 * lowercase invitation to say the stuck thing in plain words. A quiet "pull a
 * thread" submit. When the vault isn't connected (409) it softens into a gentle
 * pointer to the vault rather than an error.
 */
export function RestingState({ onPull, isBusy, noVault, error }: RestingStateProps) {
  const [stuck, setStuck] = useState('')
  const canPull = stuck.trim().length > 0 && !isBusy

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    if (!canPull) return
    onPull(stuck)
  }

  return (
    <div className="flex flex-col items-center pb-16 pt-2">
      <div className="flex flex-col items-center gap-3" aria-hidden>
        <Label tone="olive">the heart</Label>
        <WindingPath className="h-44 w-auto" />
      </div>

      <h3 className="-mt-1 max-w-md text-center font-display text-[34px] font-medium lowercase leading-[1.1] tracking-[0.005em] text-ink">
        what's tangling you up?
      </h3>
      <p className="mt-3 max-w-md text-center font-body text-[18px] leading-[1.65] text-ink-soft">
        say the stuck thing and i'll pull one thread from everything you've kept —
        one question, one connection, one next step.
      </p>

      <form onSubmit={submit} className="mt-8 flex w-full max-w-md flex-col gap-4">
        <Textarea
          id="thread-stuck"
          aria-label="the stuck thing"
          value={stuck}
          onChange={(e) => setStuck(e.target.value)}
          placeholder="say the stuck thing in plain words…"
          rows={4}
          disabled={isBusy}
        />

        {noVault ? (
          <p className="rounded-[14px] border-l-2 border-terracotta/40 bg-terracotta/8 py-3 pl-4 pr-4 font-body text-[16px] leading-[1.6] text-ink">
            connect & read your shelf first, then i'll have something to pull from.{' '}
            <Link
              to="/vault"
              className="font-medium text-clay underline decoration-terracotta/40 underline-offset-2 hover:decoration-terracotta"
            >
              open the vault
            </Link>
            .
          </p>
        ) : null}

        {error ? (
          <p
            role="alert"
            className="rounded-[14px] border-l-2 border-clay bg-clay/8 py-3 pl-4 pr-4 font-body text-[16px] leading-[1.6] text-ink"
          >
            {error}
          </p>
        ) : null}

        <div className="flex justify-center">
          <Button type="submit" variant="primary" disabled={!canPull}>
            pull a thread
            <ArrowRight weight="bold" aria-hidden className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}
