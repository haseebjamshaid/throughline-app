import type { ProfileClaim, ProfileSection } from '../../lib/api'
import { Label } from '../../ui'
import { ClaimLine } from './ClaimLine'
import { MoodPill } from './MoodPill'
import { PILL_SECTIONS, SECTION_TITLE } from './sections'

interface ClaimSectionProps {
  section: ProfileSection
  claims: readonly ProfileClaim[]
  onPin: (id: string, pinned: boolean) => void
  onEditText: (id: string, text: string) => void
  onDelete: (id: string) => void
}

/**
 * One titled group of claims. `mood` (and any pill section) renders as a soft
 * cluster of tappable pills; every other section renders as a list of serif
 * claim lines with full pin/edit/delete controls. Empty sections render nothing.
 */
export function ClaimSection({
  section,
  claims,
  onPin,
  onEditText,
  onDelete,
}: ClaimSectionProps) {
  if (claims.length === 0) return null

  const isPillSection = PILL_SECTIONS.has(section)

  return (
    <section className="flex flex-col gap-3">
      <Label tone="soft">{SECTION_TITLE[section]}</Label>
      {isPillSection ? (
        <div className="flex flex-wrap gap-2.5">
          {claims.map((claim) => (
            <MoodPill key={claim.id} claim={claim} onPin={onPin} />
          ))}
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-hairline">
          {claims.map((claim) => (
            <ClaimLine
              key={claim.id}
              claim={claim}
              onPin={onPin}
              onEditText={onEditText}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </section>
  )
}
