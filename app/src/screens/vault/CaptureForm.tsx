import { useState } from 'react'
import type { CaptureInput, Item, ItemType } from '../../lib/api'
import { CAPTURE_TYPES, TYPE_META } from '../../lib/itemMeta'
import { PlusCircle } from '@phosphor-icons/react'
import { Button, Input, Label, Panel, Select, Textarea } from '../../ui'

interface CaptureFormProps {
  /** Capture an item; resolves to the created item or throws on failure. */
  onCapture: (input: CaptureInput) => Promise<Item>
}

/** Split a comma/space separated tag string into a clean, de-duped list. */
function parseTags(raw: string): string[] {
  const seen = new Set<string>()
  return raw
    .split(/[,\n]/)
    .map((t) => t.trim().replace(/^#/, ''))
    .filter((t) => t.length > 0 && !seen.has(t) && seen.add(t))
}

/**
 * The "add to your shelf" capture panel: type select + title + serif body +
 * tags, written to the vault via POST /vault/capture. The decisive
 * "write to your vault" action carries the warm clay fill — capturing your own
 * words is the warm act.
 */
export function CaptureForm({ onCapture }: CaptureFormProps) {
  const [type, setType] = useState<ItemType>('journal')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [feeling, setFeeling] = useState('')
  const [tags, setTags] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = (): void => {
    setTitle('')
    setBody('')
    setFeeling('')
    setTags('')
  }

  const submit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    const trimmedTitle = title.trim()
    if (!trimmedTitle || busy) return
    setBusy(true)
    setError(null)
    try {
      await onCapture({
        type,
        title: trimmedTitle,
        body: body.trim() || undefined,
        feeling: feeling.trim() || undefined,
        tags: parseTags(tags),
      })
      reset()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'could not write to your vault.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel className="p-7">
      <span className="flex items-center gap-2">
        <PlusCircle weight="duotone" aria-hidden className="h-4 w-4 text-clay" />
        <Label tone="soft">add to your shelf</Label>
      </span>
      <form onSubmit={submit} className="mt-5 flex flex-col gap-5">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-[200px_1fr]">
          <Select
            id="capture-type"
            label="what kind of thing"
            value={type}
            onChange={(e) => setType(e.target.value as ItemType)}
          >
            {CAPTURE_TYPES.map((t) => (
              <option key={t} value={t}>
                {TYPE_META[t].short}
              </option>
            ))}
          </Select>
          <Input
            id="capture-title"
            label="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="what is it?"
            required
          />
        </div>

        <Textarea
          id="capture-body"
          label="in your own words"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="in your own words…"
          rows={5}
        />

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <Input
            id="capture-feeling"
            label="feeling"
            value={feeling}
            onChange={(e) => setFeeling(e.target.value)}
            placeholder="optional"
          />
          <Input
            id="capture-tags"
            label="tags"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="comma, separated"
          />
        </div>

        {error ? (
          <p
            role="alert"
            className="rounded-[12px] border-l-2 border-clay bg-clay/8 py-2 pl-3 pr-3 font-body text-[16px] leading-[1.6] text-ink"
          >
            {error}
          </p>
        ) : null}

        <div>
          <Button type="submit" variant="primary" disabled={busy || !title.trim()}>
            {busy ? 'writing' : 'write to your vault'}
          </Button>
        </div>
      </form>
    </Panel>
  )
}
