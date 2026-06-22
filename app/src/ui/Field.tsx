import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'
import { Label } from './Label'

/*
  Shared field chrome: a warm card surface with a soft inset, a soft hairline
  border, a 14px organic radius, lowercase placeholders, and a gentle terracotta
  focus ring. Warm and tactile, not a stark box.
*/
const FIELD_BASE =
  'w-full rounded-[14px] border border-border bg-card px-3.5 py-2.5 text-ink shadow-[inset_0_1px_3px_rgba(67,55,42,0.06)] outline-none transition-colors duration-150 placeholder:text-ink-soft placeholder:lowercase focus:border-terracotta focus:ring-2 focus:ring-terracotta/30 disabled:cursor-not-allowed disabled:opacity-40'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Lowercase label rendered above the field; also wires up htmlFor/id. */
  label?: string
}

/** Single-line text input. EB Garamond body so paths/tags still read warmly. */
export function Input({ label, id, className = '', ...rest }: InputProps) {
  return (
    <FieldWrap label={label} htmlFor={id}>
      <input
        id={id}
        className={`${FIELD_BASE} font-body text-[16px] tracking-[0.01em] ${className}`}
        {...rest}
      />
    </FieldWrap>
  )
}

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
}

/**
 * Multi-line text area. Serif body, because note bodies are the user's own
 * words — the reading voice of the whole library.
 */
export function Textarea({ label, id, className = '', rows = 5, ...rest }: TextareaProps) {
  return (
    <FieldWrap label={label} htmlFor={id}>
      <textarea
        id={id}
        rows={rows}
        className={`${FIELD_BASE} resize-y font-body text-[17px] leading-[1.65] ${className}`}
        {...rest}
      />
    </FieldWrap>
  )
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

/** Native select, restyled warm. Lowercase Nunito Sans label-style text. */
export function Select({ label, id, className = '', children, ...rest }: SelectProps) {
  return (
    <FieldWrap label={label} htmlFor={id}>
      <select
        id={id}
        className={`${FIELD_BASE} appearance-none font-label text-[13px] lowercase tracking-[0.02em] ${className}`}
        {...rest}
      >
        {children}
      </select>
    </FieldWrap>
  )
}

interface FieldWrapProps {
  label?: string
  htmlFor?: string
  children: React.ReactNode
}

/** Stacks a lowercase label above a field and associates it via htmlFor. */
function FieldWrap({ label, htmlFor, children }: FieldWrapProps) {
  if (!label) return <>{children}</>
  return (
    <label htmlFor={htmlFor} className="flex flex-col gap-2">
      <Label tone="soft">{label}</Label>
      {children}
    </label>
  )
}
