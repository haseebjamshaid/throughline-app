import { VAULT_FILTERS } from '../../lib/itemMeta'
import { Pill } from '../../ui'

interface FilterRowProps {
  /** Key of the active filter pill. */
  activeKey: string
  onChange: (key: string) => void
}

/** The horizontal type-filter pill row above the item list. */
export function FilterRow({ activeKey, onChange }: FilterRowProps) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Filter items by type">
      {VAULT_FILTERS.map((filter) => (
        <Pill
          key={filter.key}
          active={filter.key === activeKey}
          onClick={() => onChange(filter.key)}
        >
          {filter.label}
        </Pill>
      ))}
    </div>
  )
}
