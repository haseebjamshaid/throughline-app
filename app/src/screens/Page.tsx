import type { ReactNode } from 'react'
import { Label } from '../ui'
import { Sprig } from '../illustrations'

interface PageProps {
  /** Display title in Fraunces, lowercase. */
  title: string
  /** Optional lowercase eyebrow above the title. */
  eyebrow?: string
  /** Optional right-aligned header slot (e.g. counts, actions). */
  aside?: ReactNode
  children: ReactNode
}

/**
 * Shared screen scaffold: a left-aligned column with generous air and a large
 * lowercase serif title, separated from the body by a soft hairline carrying a
 * small sprig. Every screen sits on this so the rhythm stays consistent.
 */
export function Page({ title, eyebrow, aside, children }: PageProps) {
  return (
    <div className="mx-auto w-full max-w-4xl px-8 py-14">
      <header className="mb-12 border-b border-border pb-6">
        <div className="flex items-end justify-between gap-6">
          <div className="flex flex-col gap-2">
            {eyebrow ? (
              <span className="flex items-center gap-1.5">
                <Sprig aria-hidden className="h-3.5 w-3.5" />
                <Label tone="soft">{eyebrow}</Label>
              </span>
            ) : null}
            <h2 className="font-display text-[52px] font-medium lowercase leading-[1.0] tracking-[0.005em] text-ink">
              {title}
            </h2>
          </div>
          {aside ? <div className="shrink-0 pb-2">{aside}</div> : null}
        </div>
      </header>
      {children}
    </div>
  )
}
