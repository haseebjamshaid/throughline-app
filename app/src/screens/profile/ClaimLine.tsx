import { useState } from 'react'
import { Check, PencilSimple, PushPin, Trash, X } from '@phosphor-icons/react'
import type { ProfileClaim, ProfileConfidence } from '../../lib/api'

interface ClaimLineProps {
  claim: ProfileClaim
  /** Toggle the pin (optimistic; reconciled upstream). */
  onPin: (id: string, pinned: boolean) => void
  /** Save edited text. */
  onEditText: (id: string, text: string) => void
  /** Soft-delete the claim. */
  onDelete: (id: string) => void
}

/** Soft confidence wash per level — never shouty, warmest at "high". */
const CONFIDENCE_CLASS: Record<ProfileConfidence, string> = {
  low: 'bg-sand/50 text-ink-soft',
  medium: 'bg-gold/20 text-clay',
  high: 'bg-terracotta/15 text-clay',
}

/**
 * One line of the portrait. Shows the claim text (serif, lowercase), a quiet
 * "because of n things" annotation, a tiny confidence tag, and a trio of warm
 * controls: pin (terracotta when pinned), inline edit (pencil → field → save),
 * and delete. All edits are optimistic; the parent reconciles with the server.
 */
export function ClaimLine({ claim, onPin, onEditText, onDelete }: ClaimLineProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState(claim.text)

  const sourceCount = claim.examples.length
  const becauseLabel = `because of ${sourceCount} ${sourceCount === 1 ? 'thing' : 'things'}`

  const startEdit = (): void => {
    setDraft(claim.text)
    setIsEditing(true)
  }

  const cancelEdit = (): void => {
    setDraft(claim.text)
    setIsEditing(false)
  }

  const saveEdit = (): void => {
    const trimmed = draft.trim()
    if (trimmed && trimmed !== claim.text) onEditText(claim.id, trimmed)
    setIsEditing(false)
  }

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === 'Enter') {
      event.preventDefault()
      saveEdit()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancelEdit()
    }
  }

  if (isEditing) {
    return (
      <li className="flex items-center gap-2 py-1.5">
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="edit claim"
          className="min-w-0 flex-1 rounded-[14px] border border-border bg-card px-3 py-1.5 font-body text-[18px] lowercase leading-[1.5] text-ink shadow-[inset_0_1px_3px_rgba(67,55,42,0.06)] outline-none transition-colors duration-150 focus:border-terracotta focus:ring-2 focus:ring-terracotta/30"
        />
        <IconButton label="save" onClick={saveEdit} accent>
          <Check weight="bold" aria-hidden className="h-4 w-4" />
        </IconButton>
        <IconButton label="cancel" onClick={cancelEdit}>
          <X weight="bold" aria-hidden className="h-4 w-4" />
        </IconButton>
      </li>
    )
  }

  return (
    <li className="group flex items-baseline gap-3 py-1.5">
      <div className="min-w-0 flex-1">
        <p className="font-body text-[19px] lowercase leading-[1.5] text-ink">
          {claim.text}
        </p>
        <span className="mt-0.5 flex flex-wrap items-center gap-2">
          <span className="font-label text-[11px] lowercase tracking-[0.03em] text-ink-soft">
            {becauseLabel}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 font-label text-[10px] font-semibold lowercase tracking-[0.03em] ${CONFIDENCE_CLASS[claim.confidence]}`}
          >
            {claim.confidence}
          </span>
        </span>
      </div>
      <ClaimControls
        pinned={claim.pinned}
        onPin={() => onPin(claim.id, !claim.pinned)}
        onEdit={startEdit}
        onDelete={() => onDelete(claim.id)}
      />
    </li>
  )
}

interface ClaimControlsProps {
  pinned: boolean
  onPin: () => void
  onEdit: () => void
  onDelete: () => void
}

/**
 * The trio of warm controls. The pin stays visible (it carries state); edit and
 * delete fade in on hover/focus so the line reads calmly at rest.
 */
function ClaimControls({ pinned, onPin, onEdit, onDelete }: ClaimControlsProps) {
  return (
    <span className="flex shrink-0 items-center gap-1">
      <IconButton label={pinned ? 'unpin' : 'pin'} onClick={onPin} active={pinned}>
        <PushPin
          weight={pinned ? 'fill' : 'regular'}
          aria-hidden
          className={`h-4 w-4 ${pinned ? 'text-terracotta' : ''}`}
        />
      </IconButton>
      <span className="flex items-center gap-1 opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100">
        <IconButton label="edit" onClick={onEdit}>
          <PencilSimple aria-hidden className="h-4 w-4" />
        </IconButton>
        <IconButton label="delete" onClick={onDelete}>
          <Trash aria-hidden className="h-4 w-4" />
        </IconButton>
      </span>
    </span>
  )
}

interface IconButtonProps {
  label: string
  onClick: () => void
  children: React.ReactNode
  /** A filled-accent save button. */
  accent?: boolean
  /** Pinned/active state — keeps the warm wash on. */
  active?: boolean
}

/** A small, round, low-contrast warm icon button used across the claim line. */
function IconButton({ label, onClick, children, accent, active }: IconButtonProps) {
  const tone = accent
    ? 'bg-clay text-card hover:bg-terracotta'
    : active
      ? 'text-terracotta hover:bg-terracotta/10'
      : 'text-ink-soft hover:bg-sand/60 hover:text-ink'
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 ${tone}`}
    >
      {children}
    </button>
  )
}
