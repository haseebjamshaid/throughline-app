import { useState } from 'react'
import { ArrowRight } from '@phosphor-icons/react'
import { connectVault, isApiStatus } from '../lib/api'
import { Button, Input, Label } from '../ui'
import { BookUnderTree } from '../illustrations'

interface ConnectStepProps {
  /** Called with the indexed item count once a vault connects. */
  onConnected: (indexed: number) => void
}

/** Translate a connect failure into a friendly, actionable lowercase message. */
function connectMessage(error: unknown): string {
  if (isApiStatus(error, 0)) {
    return 'the backend is offline — start it on 127.0.0.1:8000 and try again.'
  }
  if (isApiStatus(error, 503)) {
    return 'the local model stack is not ready yet — check ollama is running.'
  }
  if (error instanceof Error && error.message) return error.message
  return 'could not open that vault — check the path and try again.'
}

/**
 * The first beat — a warm welcome and the one thing the library needs: where
 * your notes live. Nothing leaves the machine; it reads them in place. On a
 * successful connect we hand the indexed count up so the next beat can read.
 */
export function ConnectStep({ onConnected }: ConnectStepProps) {
  const [path, setPath] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    const trimmed = path.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError(null)
    try {
      const connection = await connectVault(trimmed)
      onConnected(connection.indexed)
    } catch (err: unknown) {
      setError(connectMessage(err))
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center text-center">
      <BookUnderTree aria-hidden className="h-32 w-auto" />
      <Label tone="olive" className="mt-4">
        welcome
      </Label>
      <h2 className="mt-2 max-w-lg font-display text-[38px] font-medium lowercase leading-[1.08] tracking-[0.005em] text-ink">
        let's find the you in your notes
      </h2>
      <p className="mt-4 max-w-md font-body text-[18px] leading-[1.65] text-ink-soft">
        point me at your obsidian vault — the films, songs, books, quotes and
        private notes you've kept. nothing leaves this machine; i read them right
        where they sit.
      </p>

      <form onSubmit={submit} className="mt-8 flex w-full max-w-md flex-col gap-4 text-left">
        <Input
          id="onboard-vault-path"
          label="where your vault lives"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="/users/you/desktop/throughline-vault"
          autoComplete="off"
          spellCheck={false}
        />
        <p className="font-body text-[14px] italic leading-[1.5] text-ink-soft">
          made one with the setup script? it lives at ~/desktop/throughline-vault.
        </p>
        {error ? (
          <p
            role="alert"
            className="rounded-[12px] border-l-2 border-clay bg-clay/8 py-2.5 pl-3.5 pr-3.5 font-body text-[16px] leading-[1.6] text-ink"
          >
            {error}
          </p>
        ) : null}
        <Button type="submit" variant="primary" disabled={busy} block>
          {busy ? 'opening your shelf…' : 'open my shelf'}
          {!busy ? <ArrowRight weight="bold" aria-hidden className="h-4 w-4" /> : null}
        </Button>
      </form>
    </div>
  )
}
