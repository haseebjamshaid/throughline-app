import { useState } from 'react'
import { Leaf, CloudSlash, CircleNotch } from '@phosphor-icons/react'
import { useHealth } from '../lib/useHealth'
import { ModelsPanel } from './ModelsPanel'

type Tone = 'muted' | 'active' | 'warn'

interface PillVisual {
  Icon: typeof Leaf
  spin: boolean
  iconClassName: string
  label: string
  tone: Tone
}

/** Map the polled health into the pill's icon, label, and tone. */
function pillVisual(
  status: ReturnType<typeof useHealth>['status'],
  isOnline: boolean,
  isLoading: boolean,
): PillVisual {
  if (isLoading) {
    return { Icon: CircleNotch, spin: true, iconClassName: 'text-ink-soft', label: 'connecting', tone: 'muted' }
  }
  if (!isOnline || !status) {
    return { Icon: CloudSlash, spin: false, iconClassName: 'text-ink-soft', label: 'offline', tone: 'muted' }
  }
  if (status.ollamaReachable && status.modelsPresent) {
    // Fully ready — the warm leaf.
    return { Icon: Leaf, spin: false, iconClassName: 'text-olive', label: 'online', tone: 'active' }
  }
  // Backend is up, but the local model stack isn't fully ready yet.
  const detail = !status.ollamaReachable ? 'ollama down' : 'no models'
  return { Icon: Leaf, spin: false, iconClassName: 'text-ink-soft', label: `online · ${detail}`, tone: 'warn' }
}

/**
 * Header status indicator that doubles as the Models-panel trigger. Reflects
 * backend reachability and, when online, whether Ollama + models are ready.
 * Clicking it opens a quiet warm panel to load/unload models from RAM.
 */
export function StatusPill() {
  const { status, isOnline, isLoading } = useHealth()
  const [open, setOpen] = useState(false)
  const visual = pillVisual(status, isOnline, isLoading)

  return (
    <div className="relative">
      <Pill {...visual} onClick={() => setOpen((prev) => !prev)} expanded={open} />
      <ModelsPanel open={open} onClose={() => setOpen(false)} />
    </div>
  )
}

interface PillProps extends PillVisual {
  onClick: () => void
  expanded: boolean
}

const TONE_TEXT: Record<Tone, string> = {
  muted: 'text-ink-soft',
  active: 'text-ink',
  warn: 'text-ink-soft',
}

function Pill({ Icon, spin, iconClassName, label, tone, onClick, expanded }: PillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-haspopup="dialog"
      aria-expanded={expanded}
      title="manage models in ram"
      className={`inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 font-label text-[12px] font-medium lowercase tracking-[0.03em] shadow-soft transition-colors duration-150 outline-none hover:bg-paper focus-visible:ring-2 focus-visible:ring-terracotta/50 ${TONE_TEXT[tone]}`}
    >
      <Icon
        weight={tone === 'active' ? 'fill' : 'regular'}
        aria-hidden
        className={`h-3.5 w-3.5 ${iconClassName} ${spin ? 'animate-spin' : ''}`}
      />
      {label}
    </button>
  )
}
