import type { ProfileView } from './sections'
import { Pill } from '../../ui'

interface ViewToggleProps {
  view: ProfileView
  onChange: (view: ProfileView) => void
}

/** The two calm views, in order, with their lowercase labels. */
const VIEWS: readonly { key: ProfileView; label: string }[] = [
  { key: 'creative', label: 'creative slice' },
  { key: 'deeper', label: 'deeper threads' },
]

/**
 * A calm segmented toggle between the two portrait views. Reuses the warm Pill,
 * so the active slice gets a soft terracotta wash and the other stays quiet.
 */
export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="flex gap-2.5" role="group" aria-label="profile view">
      {VIEWS.map(({ key, label }) => (
        <Pill key={key} active={view === key} onClick={() => onChange(key)}>
          {label}
        </Pill>
      ))}
    </div>
  )
}
