import type { PaletteColor } from '../../lib/api'
import { Label } from '../../ui'

interface PaletteRowProps {
  palette: readonly PaletteColor[]
}

/**
 * The portrait's colours, as a row of rounded warm chips — a soft swatch over a
 * lowercase name and its hex. The library's read on the hues you reach for.
 */
export function PaletteRow({ palette }: PaletteRowProps) {
  if (palette.length === 0) return null
  return (
    <section className="flex flex-col gap-3">
      <Label tone="soft">palette</Label>
      <div className="flex flex-wrap gap-3">
        {palette.map((color, index) => (
          <div
            key={`${color.hex}-${index}`}
            className="flex items-center gap-2.5 rounded-full border border-border bg-card py-1.5 pl-1.5 pr-3.5 shadow-soft"
          >
            <span
              aria-hidden
              className="h-7 w-7 shrink-0 rounded-full border border-hairline"
              style={{ backgroundColor: color.hex }}
            />
            <span className="flex flex-col leading-tight">
              <span className="font-label text-[12px] font-medium lowercase tracking-[0.02em] text-ink">
                {color.name}
              </span>
              <span className="numerals-old font-label text-[10px] lowercase tracking-[0.04em] text-ink-soft">
                {color.hex.toLowerCase()}
              </span>
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
