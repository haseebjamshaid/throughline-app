import { useState } from 'react'
import { Button, Input, Label, Panel } from '../../ui'

/** Empty by default — the user types the absolute path to their own vault. */
const DEFAULT_VAULT_PATH = ''

interface ConnectPanelProps {
  isConnecting: boolean
  error: string | null
  onConnect: (path: string) => void
}

/**
 * The elegant, centered "point at your vault" panel shown when no vault is
 * connected. Prefilled with the sample-vault path so connecting is one click.
 */
export function ConnectPanel({ isConnecting, error, onConnect }: ConnectPanelProps) {
  const [path, setPath] = useState(DEFAULT_VAULT_PATH)

  const submit = (event: React.FormEvent): void => {
    event.preventDefault()
    const trimmed = path.trim()
    if (trimmed && !isConnecting) onConnect(trimmed)
  }

  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Panel className="w-full max-w-xl px-9 py-10">
        <Label tone="soft">vault · not yet connected</Label>
        <h3 className="mt-3 font-display text-[34px] font-medium lowercase leading-[1.05] tracking-[0.005em] text-ink">
          point at your vault
        </h3>
        <p className="mt-4 font-body text-[18px] leading-[1.65] text-ink">
          give the machine the absolute path to your notes. nothing leaves this
          machine — it reads them in place.
        </p>

        <form onSubmit={submit} className="mt-8 flex flex-col gap-5">
          <Input
            id="vault-path"
            label="absolute path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/your/vault"
            autoComplete="off"
            spellCheck={false}
          />
          {error ? (
            <p
              role="alert"
              className="rounded-[12px] border-l-2 border-clay bg-clay/8 py-2 pl-3 pr-3 font-body text-[16px] leading-[1.6] text-ink"
            >
              {error}
            </p>
          ) : null}
          <Button type="submit" variant="primary" disabled={isConnecting} block>
            {isConnecting ? 'connecting' : 'connect'}
          </Button>
        </form>
      </Panel>
    </div>
  )
}
