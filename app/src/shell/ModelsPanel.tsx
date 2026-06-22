import { useEffect, useRef } from 'react'
import { useModels } from '../lib/useModels'
import type { ModelRole, ModelStatus } from '../lib/api'
import { Label } from '../ui'

interface ModelsPanelProps {
  /** Whether the panel is open (drives polling + render). */
  open: boolean
  /** Called when the panel should close (outside click / Escape). */
  onClose: () => void
}

const ROLE_LABEL: Record<ModelRole, string> = {
  embed: 'embed',
  text: 'text',
  vision: 'vision',
  other: 'other',
}

/** Format a model's resident RAM, e.g. `5400 mb`, or an em dash when idle. */
function formatRam(model: ModelStatus): string {
  if (!model.loaded || model.sizeMb === null) return '—'
  return `${Math.round(model.sizeMb).toLocaleString()} mb`
}

/**
 * A quiet panel listing the configured models with a load/unload toggle each,
 * role + RAM, and an "unload all" action. Polls while `open`. A warm rounded
 * card with a soft warm shadow — depth from the lift, not hard borders.
 */
export function ModelsPanel({ open, onClose }: ModelsPanelProps) {
  const { models, isLoading, isOnline, pending, load, unload, unloadEverything } =
    useModels(open)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent): void => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose])

  if (!open) return null

  const anyLoaded = (models ?? []).some((m) => m.loaded)

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-label="model controls"
      className="absolute right-0 top-full z-30 mt-3 w-80 rounded-[18px] border border-border bg-card p-4 shadow-lift"
    >
      <div className="mb-3 flex items-center justify-between px-1">
        <Label tone="soft">models in ram</Label>
        <button
          type="button"
          onClick={() => void unloadEverything()}
          disabled={!isOnline || !anyLoaded}
          className="rounded-full border border-border px-2.5 py-1 font-label text-[11px] font-medium lowercase tracking-[0.03em] text-ink-soft transition-colors duration-150 hover:bg-sand/50 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-ink-soft"
        >
          unload all
        </button>
      </div>

      {isLoading && (
        <p className="px-1 py-3 font-label text-[12px] lowercase tracking-[0.03em] text-ink-soft">
          loading
        </p>
      )}

      {!isLoading && !isOnline && (
        <p className="px-1 py-3 font-label text-[12px] lowercase tracking-[0.03em] text-ink-soft">
          backend offline
        </p>
      )}

      {!isLoading && isOnline && (
        <ul className="flex flex-col">
          {(models ?? []).map((model) => (
            <ModelRow
              key={model.name}
              model={model}
              busy={pending.has(model.name)}
              onToggle={() =>
                model.loaded ? void unload(model.name) : void load(model.name)
              }
            />
          ))}
        </ul>
      )}
    </div>
  )
}

interface ModelRowProps {
  model: ModelStatus
  busy: boolean
  onToggle: () => void
}

function ModelRow({ model, busy, onToggle }: ModelRowProps) {
  const canToggle = model.installed && !busy
  return (
    <li className="flex items-center gap-3 border-b border-hairline px-1 py-2.5 last:border-b-0">
      <span
        className={`h-1.5 w-1.5 shrink-0 rounded-full ${model.loaded ? 'bg-terracotta' : 'bg-ink-soft/50'}`}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="truncate font-body text-[15px] text-ink">{model.name}</div>
        <div className="font-label text-[11px] lowercase tracking-[0.03em] text-ink-soft">
          {ROLE_LABEL[model.role]}
          {!model.installed && ' · not installed'}
          {model.loaded && ` · ${formatRam(model)}`}
        </div>
      </div>
      <Toggle on={model.loaded} disabled={!canToggle} onClick={onToggle} />
    </li>
  )
}

interface ToggleProps {
  on: boolean
  disabled: boolean
  onClick: () => void
}

/** A quiet on/off switch — orange knob when loaded, recessed when idle. */
function Toggle({ on, disabled, onClick }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      disabled={disabled}
      onClick={onClick}
      className={`relative h-5 w-9 shrink-0 rounded-full border transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-terracotta/50 disabled:cursor-not-allowed disabled:opacity-40 ${
        on ? 'border-terracotta/50 bg-terracotta/20' : 'border-border bg-sand/40'
      }`}
    >
      <span
        className={`absolute top-0.5 h-3.5 w-3.5 rounded-full transition-all duration-150 ${
          on ? 'left-[18px] bg-terracotta' : 'left-0.5 bg-ink-soft/60'
        }`}
      />
    </button>
  )
}
