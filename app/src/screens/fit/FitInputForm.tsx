import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ImageSquare } from '@phosphor-icons/react'
import type { FitInput, FitKind } from '../../lib/api'
import { Button, Label, Textarea } from '../../ui'
import { LeafOnScale } from '../../illustrations'

interface FitInputFormProps {
  /** Run a fit check on the assembled input. */
  onCheck: (input: FitInput) => void
  /** True while a check is in flight (disables the controls). */
  isBusy: boolean
  /** Set when the last check failed because no vault is connected (409). */
  noVault: boolean
  /** Set when connected but no profile has been generated yet (409). */
  noProfile: boolean
  /** Any unexpected error message, or `null`. */
  error: string | null
}

const KINDS: readonly { kind: FitKind; label: string }[] = [
  { kind: 'caption', label: 'a caption' },
  { kind: 'song', label: 'a song' },
  { kind: 'image', label: 'an image' },
]

const PLACEHOLDER: Record<FitKind, string> = {
  caption: 'paste the caption or a few lines of writing…',
  song: 'name the song, or describe how it sounds…',
  image: '',
}

/**
 * The calm resting page for fit check — a leaf balanced on a scale and a
 * lowercase invitation to hold something up against everything you are. Choose
 * what kind of thing it is, give it (text, or an image), and check the fit.
 * When the vault or profile isn't ready (409) it softens into a gentle pointer
 * rather than an error.
 */
export function FitInputForm({
  onCheck,
  isBusy,
  noVault,
  noProfile,
  error,
}: FitInputFormProps) {
  const [kind, setKind] = useState<FitKind>('caption')
  const [text, setText] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const hasInput = kind === 'image' ? image !== null : text.trim().length > 0
  const canCheck = hasInput && !isBusy

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    if (!canCheck) return
    onCheck(
      kind === 'image'
        ? { kind, image: image ?? undefined }
        : { kind, text: text.trim() },
    )
  }

  return (
    <div className="flex flex-col items-center pb-16 pt-2">
      <div className="flex flex-col items-center gap-3" aria-hidden>
        <Label tone="olive">the honest mirror</Label>
        <LeafOnScale className="h-40 w-auto" />
      </div>

      <h3 className="-mt-1 max-w-md text-center font-display text-[34px] font-medium lowercase leading-[1.1] tracking-[0.005em] text-ink">
        is this you?
      </h3>
      <p className="mt-3 max-w-md text-center font-body text-[18px] leading-[1.65] text-ink-soft">
        hold something up against everything you've kept, and i'll tell you —
        honestly — how close to you it sits, and where it drifts.
      </p>

      <form onSubmit={submit} className="mt-8 flex w-full max-w-md flex-col gap-5">
        <fieldset className="flex flex-col gap-2">
          <Label tone="soft">what is it</Label>
          <div className="flex gap-2" role="radiogroup" aria-label="what kind of thing">
            {KINDS.map((option) => {
              const active = option.kind === kind
              return (
                <button
                  key={option.kind}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setKind(option.kind)}
                  className={`flex-1 rounded-full border px-3 py-2 font-label text-[13px] font-semibold lowercase tracking-[0.01em] transition-all duration-150 ${
                    active
                      ? 'border-terracotta/50 bg-terracotta/12 text-clay shadow-soft'
                      : 'border-border bg-card text-ink-soft hover:bg-paper'
                  }`}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </fieldset>

        {kind === 'image' ? (
          <div className="flex flex-col gap-2">
            <Label tone="soft">the image</Label>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex items-center justify-center gap-2 rounded-[14px] border border-dashed border-border bg-card px-4 py-6 font-label text-[14px] lowercase text-ink-soft shadow-[inset_0_1px_3px_rgba(67,55,42,0.06)] transition-colors duration-150 hover:border-terracotta/50 hover:text-clay"
            >
              <ImageSquare aria-hidden className="h-5 w-5" />
              {image ? image.name : 'choose an image to weigh'}
            </button>
          </div>
        ) : (
          <Textarea
            id="fit-text"
            aria-label="what you're holding up"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={PLACEHOLDER[kind]}
            rows={4}
            disabled={isBusy}
          />
        )}

        {noVault ? (
          <p className="rounded-[14px] border-l-2 border-terracotta/40 bg-terracotta/8 py-3 pl-4 pr-4 font-body text-[16px] leading-[1.6] text-ink">
            connect & read your shelf first, so there's a you to measure against.{' '}
            <Link
              to="/vault"
              className="font-medium text-clay underline decoration-terracotta/40 underline-offset-2 hover:decoration-terracotta"
            >
              open the vault
            </Link>
            .
          </p>
        ) : null}

        {noProfile ? (
          <p className="rounded-[14px] border-l-2 border-gold/50 bg-gold/10 py-3 pl-4 pr-4 font-body text-[16px] leading-[1.6] text-ink">
            sketch your profile first — that's the picture i hold things up
            against.{' '}
            <Link
              to="/profile"
              className="font-medium text-clay underline decoration-gold/50 underline-offset-2 hover:decoration-gold"
            >
              draw my profile
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
          <Button type="submit" variant="primary" disabled={!canCheck}>
            check the fit
            <ArrowRight weight="bold" aria-hidden className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}
