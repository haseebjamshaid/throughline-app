import { Link } from 'react-router-dom'
import { Sparkle } from '@phosphor-icons/react'
import { Button, Label, Panel } from '../../ui'
import { BookUnderTree } from '../../illustrations'

interface EmptyProfileProps {
  /** Kick off generation (slow). */
  onGenerate: () => void
  /** True while generation is in flight. */
  isGenerating: boolean
  /** Set when the last attempt failed because no vault is connected (409). */
  noVault: boolean
  /** Any other generate error message, or `null`. */
  error: string | null
}

/**
 * The honest, lowercase empty state: an open book under a tree, an invitation to
 * read your shelf and generate the picture of you, and a primary "generate
 * profile" button. When the vault isn't connected (409), it softens into a
 * gentle pointer to the vault page instead of an error.
 */
export function EmptyProfile({
  onGenerate,
  isGenerating,
  noVault,
  error,
}: EmptyProfileProps) {
  return (
    <div className="flex min-h-[55vh] items-center justify-center">
      <Panel className="w-full max-w-xl px-9 py-11 text-center">
        <BookUnderTree className="mx-auto h-auto w-full max-w-[260px] opacity-95" />
        <Label tone="soft" className="mt-7 block">
          profile · not drawn yet
        </Label>
        <h3 className="mt-3 font-display text-[32px] font-medium lowercase leading-[1.1] tracking-[0.005em] text-ink">
          no profile yet
        </h3>
        <p className="mx-auto mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink">
          read your shelf, then generate the picture of you — drawn from your
          library, not a form you fill in.
        </p>

        {noVault ? (
          <p className="mx-auto mt-6 max-w-md rounded-[14px] border-l-2 border-terracotta/40 bg-terracotta/8 py-3 pl-4 pr-4 text-left font-body text-[16px] leading-[1.6] text-ink">
            connect & read your vault first.{' '}
            <Link
              to="/vault"
              className="font-medium text-clay underline decoration-terracotta/40 underline-offset-2 hover:decoration-terracotta"
            >
              open the vault
            </Link>{' '}
            to point the machine at your notes.
          </p>
        ) : null}

        {error ? (
          <p
            role="alert"
            className="mx-auto mt-6 max-w-md rounded-[14px] border-l-2 border-clay bg-clay/8 py-3 pl-4 pr-4 text-left font-body text-[16px] leading-[1.6] text-ink"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-8 flex justify-center">
          <Button variant="primary" onClick={onGenerate} disabled={isGenerating}>
            <Sparkle
              weight={isGenerating ? 'fill' : 'regular'}
              aria-hidden
              className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`}
            />
            {isGenerating ? 'reading your shelf…' : 'generate profile'}
          </Button>
        </div>

        {isGenerating ? (
          <p className="mt-4 font-body text-[15px] italic leading-[1.5] text-ink-soft">
            drawing the picture of you — this can take a moment.
          </p>
        ) : null}
      </Panel>
    </div>
  )
}
