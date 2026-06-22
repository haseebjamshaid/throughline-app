import { ArrowsClockwise, Shuffle } from '@phosphor-icons/react'
import { useProfile } from '../../lib/appState'
import { Button, Label } from '../../ui'

const MAX_SEED = 1_000_000
const INPUT_CLASS =
  'rounded-[14px] border border-border bg-card px-3 py-2 font-body text-[16px] text-ink shadow-[inset_0_1px_3px_rgba(67,55,42,0.06)] outline-none transition-colors duration-150 focus:border-terracotta focus:ring-2 focus:ring-terracotta/30 disabled:cursor-not-allowed disabled:opacity-40'

function clampTemperature(value: number): number {
  if (Number.isNaN(value)) return 0
  return Math.round(Math.max(0, Math.min(2, value)) * 10) / 10
}

function cleanSeed(value: number): number {
  if (Number.isNaN(value)) return 0
  return Math.max(0, Math.min(MAX_SEED, Math.floor(value)))
}

/**
 * The portrait's sampling knobs, made editable: temperature (how far it may
 * wander) and seed (which draw). The values live in the shared profile hook, so
 * they persist across screen unmount/remount — switching tabs mid-redraw keeps
 * exactly what you set. At temperature 0 a redraw is identical; raise it — or
 * shuffle the seed — for a different take.
 */
export function GenerationControls() {
  const {
    genTemperature,
    genSeed,
    setGenTemperature,
    setGenSeed,
    isGenerating,
    generate,
  } = useProfile()

  return (
    <section className="rounded-[20px] border border-border bg-card/60 px-6 py-5 shadow-soft">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <div className="flex flex-col gap-1">
          <Label tone="clay">generation</Label>
          <p className="max-w-sm font-body text-[14px] italic leading-[1.5] text-ink-soft">
            temperature 0 redraws the same portrait every time. raise it, or
            shuffle the seed, for a different take.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5">
            <Label tone="soft">temperature</Label>
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={genTemperature}
              onChange={(e) => setGenTemperature(clampTemperature(Number(e.target.value)))}
              disabled={isGenerating}
              className={`w-24 ${INPUT_CLASS}`}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <Label tone="soft">seed</Label>
            <span className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={MAX_SEED}
                step={1}
                value={genSeed}
                onChange={(e) => setGenSeed(cleanSeed(Number(e.target.value)))}
                disabled={isGenerating}
                className={`w-28 numerals-old ${INPUT_CLASS}`}
              />
              <button
                type="button"
                aria-label="shuffle the seed"
                title="shuffle the seed"
                onClick={() => setGenSeed(Math.floor(Math.random() * MAX_SEED))}
                disabled={isGenerating}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-card text-ink-soft shadow-soft transition-colors duration-150 hover:text-clay disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Shuffle weight="bold" aria-hidden className="h-4 w-4" />
              </button>
            </span>
          </label>

          <Button
            variant="primary"
            onClick={() =>
              void generate({ temperature: genTemperature, seed: genSeed, force: true })
            }
            disabled={isGenerating}
          >
            <ArrowsClockwise
              weight="bold"
              aria-hidden
              className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`}
            />
            {isGenerating ? 'drawing…' : 'redraw'}
          </Button>
        </div>
      </div>
    </section>
  )
}
