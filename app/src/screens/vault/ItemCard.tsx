import { useState } from 'react'
import type { Icon } from '@phosphor-icons/react'
import {
  FilmReel,
  MusicNote,
  BookOpen,
  Quotes,
  Mountains,
  Wind,
  Compass,
  NotePencil,
  Image as ImageIcon,
  Leaf,
  Lock,
  PencilSimple,
  Trash,
} from '@phosphor-icons/react'
import type { Item, ItemPatch, ItemType } from '../../lib/api'
import { TYPE_META } from '../../lib/itemMeta'
import { Label } from '../../ui'
import { ItemEditForm } from './ItemEditForm'

interface ItemCardProps {
  item: Item
  /** Catalog number in the curated library, e.g. 14 → "no. 014". */
  catalogNo: number
  /** Save an edit (metadata and/or body) for this item. */
  onSave: (id: string, patch: ItemPatch) => Promise<void>
  /** Remove this item from the shelf (deletes the file + prunes the index). */
  onDelete: (id: string) => Promise<void>
}

/** A nature-leaning Phosphor icon per item type. `note` is the fallback. */
const TYPE_ICON: Record<ItemType, Icon> = {
  movie: FilmReel,
  song: MusicNote,
  book: BookOpen,
  quote: Quotes,
  ambition: Mountains,
  fear: Wind,
  experience: Compass,
  journal: NotePencil,
  image: ImageIcon,
  note: Leaf,
}

/** Trim a body to a short serif preview without cutting mid-word too harshly. */
function preview(body: string, max = 150): string {
  const clean = body.replace(/\s+/g, ' ').trim()
  if (clean.length <= max) return clean
  return `${clean.slice(0, max).trimEnd()}…`
}

/** Build the italic meta line: feeling · #tag #tag, omitting empty parts. */
function metaLine(item: Item): string {
  const parts: string[] = []
  if (item.feeling) parts.push(item.feeling)
  if (item.tags.length > 0) parts.push(item.tags.map((t) => `#${t}`).join(' '))
  return parts.join(' · ')
}

const CARD_BASE =
  'flex h-full flex-col rounded-[20px] border border-border bg-card p-6 shadow-soft'
const ACTION_BTN =
  'flex h-7 w-7 items-center justify-center rounded-full text-ink-soft transition-colors duration-150 hover:bg-paper hover:text-clay disabled:opacity-40'

/**
 * One vault item as a warm rounded "cover" card. View mode shows the type, an
 * optional private pill, the title, an italic meta line, a body preview, and a
 * footer with the catalog number plus edit + remove actions. Editing swaps the
 * card for an inline form; removing asks for a quiet confirm in the footer. All
 * lowercase, warm vintage.
 */
export function ItemCard({ item, catalogNo, onSave, onDelete }: ItemCardProps) {
  const [mode, setMode] = useState<'view' | 'editing' | 'confirming'>('view')
  const [isBusy, setIsBusy] = useState(false)

  const typeLabel = TYPE_META[item.type].label
  const TypeIcon = TYPE_ICON[item.type] ?? Leaf
  const meta = metaLine(item)
  const isPrivate = item.locked || item.isSelf
  const no = `no. ${String(catalogNo).padStart(3, '0')}`

  if (mode === 'editing') {
    return (
      <article className={CARD_BASE}>
        <ItemEditForm
          item={item}
          isBusy={isBusy}
          onCancel={() => setMode('view')}
          onSubmit={async (patch) => {
            setIsBusy(true)
            try {
              await onSave(item.id, patch)
              setMode('view')
            } catch {
              // keep the form open so the user can adjust + retry
            } finally {
              setIsBusy(false)
            }
          }}
        />
      </article>
    )
  }

  const confirmDelete = async (): Promise<void> => {
    setIsBusy(true)
    try {
      await onDelete(item.id)
      // success → this card unmounts as the list drops the item
    } catch {
      setIsBusy(false)
      setMode('view')
    }
  }

  return (
    <article
      className={`group ${CARD_BASE} transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lift`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2">
          <TypeIcon weight="duotone" aria-hidden className="h-4 w-4 text-olive" />
          <Label tone="soft">{typeLabel}</Label>
        </span>
        {isPrivate ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-sand/40 px-2 py-0.5 font-label text-[10px] font-medium lowercase tracking-[0.03em] text-ink-soft">
            <Lock weight="fill" aria-hidden className="h-2.5 w-2.5" />
            private
          </span>
        ) : null}
      </div>

      <h3 className="mt-3 font-display text-[26px] font-medium lowercase leading-[1.12] tracking-[0.005em] text-ink">
        {item.title}
      </h3>

      {meta ? (
        <p className="mt-2 font-body text-[15px] italic leading-[1.5] text-ink-soft">
          {meta}
        </p>
      ) : null}

      {item.body ? (
        <p className="mt-3 font-body text-[15px] leading-[1.6] text-ink/85">
          {preview(item.body)}
        </p>
      ) : null}

      <div className="mt-5 flex items-center justify-between gap-3 border-t border-hairline pt-3">
        {mode === 'confirming' ? (
          <>
            <span className="font-body text-[14px] italic leading-[1.4] text-ink-soft">
              remove from your shelf?
            </span>
            <span className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => void confirmDelete()}
                disabled={isBusy}
                className="font-label text-[13px] font-semibold lowercase tracking-[0.02em] text-clay underline decoration-clay/40 underline-offset-2 transition-colors duration-150 hover:decoration-clay disabled:opacity-40"
              >
                {isBusy ? 'removing…' : 'remove'}
              </button>
              <button
                type="button"
                onClick={() => setMode('view')}
                disabled={isBusy}
                className="font-label text-[13px] font-medium lowercase tracking-[0.02em] text-ink-soft transition-colors duration-150 hover:text-ink disabled:opacity-40"
              >
                cancel
              </button>
            </span>
          </>
        ) : (
          <>
            <span className="numerals-old font-label text-[12px] font-semibold tracking-[0.02em] text-terracotta">
              {no}
            </span>
            <span className="flex items-center gap-1">
              <button
                type="button"
                aria-label={`edit ${item.title}`}
                onClick={() => setMode('editing')}
                className={ACTION_BTN}
              >
                <PencilSimple weight="bold" aria-hidden className="h-4 w-4" />
              </button>
              <button
                type="button"
                aria-label={`remove ${item.title}`}
                onClick={() => setMode('confirming')}
                className={ACTION_BTN}
              >
                <Trash weight="bold" aria-hidden className="h-4 w-4" />
              </button>
            </span>
          </>
        )}
      </div>
    </article>
  )
}
