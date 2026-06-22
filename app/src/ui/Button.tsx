import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'default' | 'primary' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  /**
   * `default` is a soft warm outline. `primary` is a clay fill with cream text —
   * the decisive write/commit action and the thread's action. `danger` is a
   * muted olive-edged variant.
   */
  variant?: ButtonVariant
  /** Full-width block button. */
  block?: boolean
}

/**
 * A warm, rounded (pill) lowercase button. Hover is gentle — a slight lift and
 * lighten under ≤150ms. Nunito Sans label text. Reduced-motion is handled
 * globally in index.css.
 */
const BASE =
  'inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-label text-[14px] font-semibold lowercase tracking-[0.01em] transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:cursor-not-allowed disabled:opacity-40'

const VARIANT: Record<ButtonVariant, string> = {
  default:
    'border border-border bg-card text-ink shadow-soft hover:-translate-y-px hover:bg-paper hover:shadow-lift active:translate-y-0',
  primary:
    'bg-clay text-card shadow-soft hover:-translate-y-px hover:bg-terracotta hover:shadow-lift active:translate-y-0',
  danger:
    'border border-olive/40 bg-transparent text-olive hover:bg-olive/10 hover:border-olive/60 active:bg-olive/15',
}

export function Button({
  children,
  variant = 'default',
  block,
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BASE} ${VARIANT[variant]} ${block ? 'w-full' : ''} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
