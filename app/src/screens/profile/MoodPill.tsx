import { PushPin } from '@phosphor-icons/react'
import type { ProfileClaim } from '../../lib/api'

interface MoodPillProps {
  claim: ProfileClaim
  onPin: (id: string, pinned: boolean) => void
}

/**
 * A mood as a soft, rounded pill — the gentlest way to wear a feeling. Pinned
 * pills carry a small terracotta tack and a warmer wash; tap the tack to toggle.
 * The "because of n things" count rides along quietly as a title for hover.
 */
export function MoodPill({ claim, onPin }: MoodPillProps) {
  const sourceCount = claim.examples.length
  const title = `because of ${sourceCount} ${sourceCount === 1 ? 'thing' : 'things'}`
  const stateClass = claim.pinned
    ? 'border-terracotta/50 bg-terracotta/15 text-ink'
    : 'border-border bg-sand/40 text-ink-soft hover:bg-sand/70 hover:text-ink'
  return (
    <button
      type="button"
      onClick={() => onPin(claim.id, !claim.pinned)}
      title={title}
      aria-pressed={claim.pinned}
      aria-label={`${claim.text} — ${claim.pinned ? 'unpin' : 'pin'}`}
      className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-body text-[16px] lowercase leading-none transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 ${stateClass}`}
    >
      {claim.pinned ? (
        <PushPin weight="fill" aria-hidden className="h-3 w-3 text-terracotta" />
      ) : null}
      {claim.text}
    </button>
  )
}
