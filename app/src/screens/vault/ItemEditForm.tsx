import { useState } from 'react'
import type { Item, ItemPatch, ItemType } from '../../lib/api'
import { TYPE_META } from '../../lib/itemMeta'
import { Button, Input, Label, Select, Textarea } from '../../ui'

/** Types a user can assign when editing (image included so a mis-typed item can be fixed). */
const EDITABLE_TYPES: readonly ItemType[] = [
  'movie',
  'song',
  'book',
  'quote',
  'ambition',
  'fear',
  'experience',
  'journal',
  'note',
  'image',
]

interface ItemEditFormProps {
  item: Item
  /** True while a save is in flight (disables the controls). */
  isBusy: boolean
  /** Save the assembled patch. */
  onSubmit: (patch: ItemPatch) => void
  /** Abandon the edit and return to the card. */
  onCancel: () => void
}

/**
 * Inline edit form for one vault item, seeded from its current values. Saves the
 * type, title, feeling, tags, and the note body — changing the body re-embeds the
 * item so search / profile / thread reflect the edit. All lowercase, warm.
 */
export function ItemEditForm({ item, isBusy, onSubmit, onCancel }: ItemEditFormProps) {
  const [type, setType] = useState<ItemType>(item.type)
  const [title, setTitle] = useState(item.title)
  const [feeling, setFeeling] = useState(item.feeling ?? '')
  const [tags, setTags] = useState(item.tags.join(', '))
  const [body, setBody] = useState(item.body)

  const canSave = title.trim().length > 0 && !isBusy

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    if (!canSave) return
    onSubmit({
      type,
      title: title.trim(),
      feeling: feeling.trim(),
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      body,
    })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <Label tone="clay">editing</Label>
      <Select
        id={`edit-type-${item.id}`}
        label="type"
        value={type}
        onChange={(e) => setType(e.target.value as ItemType)}
        disabled={isBusy}
      >
        {EDITABLE_TYPES.map((t) => (
          <option key={t} value={t}>
            {TYPE_META[t].label}
          </option>
        ))}
      </Select>
      <Input
        id={`edit-title-${item.id}`}
        label="title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={isBusy}
      />
      <Input
        id={`edit-feeling-${item.id}`}
        label="feeling"
        value={feeling}
        onChange={(e) => setFeeling(e.target.value)}
        placeholder="loved · liked · …"
        disabled={isBusy}
      />
      <Input
        id={`edit-tags-${item.id}`}
        label="tags"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        placeholder="comma, separated"
        disabled={isBusy}
      />
      <Textarea
        id={`edit-body-${item.id}`}
        label="the note"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
        disabled={isBusy}
      />
      <div className="flex gap-2 pt-1">
        <Button type="submit" variant="primary" disabled={!canSave}>
          {isBusy ? 'saving…' : 'save'}
        </Button>
        <Button type="button" variant="default" onClick={onCancel} disabled={isBusy}>
          cancel
        </Button>
      </div>
    </form>
  )
}
