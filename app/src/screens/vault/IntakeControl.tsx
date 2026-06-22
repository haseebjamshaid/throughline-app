import { BookOpen } from '@phosphor-icons/react'
import { useIntake } from '../../lib/appState'
import { Button, Label, Meter, Panel } from '../../ui'

/**
 * The "read your shelf" control: starts intake, subscribes to the SSE progress
 * stream, and renders a slim cream meter plus a lowercase
 * "reading n of m · <current title>" status. pause/resume hit their endpoints.
 */
export function IntakeControl() {
  const { state, progress, error, start, pause, resume } = useIntake()

  const done = progress?.done ?? 0
  const total = progress?.total ?? 0
  const isActive = state === 'running' || state === 'paused'

  return (
    <Panel className="p-7">
      <div className="flex items-center justify-between gap-4">
        <span className="flex items-center gap-2">
          <BookOpen weight="duotone" aria-hidden className="h-4 w-4 text-olive" />
          <Label tone="soft">read your shelf</Label>
        </span>
        <div className="flex gap-3">
          {!isActive ? (
            <Button onClick={() => void start()}>
              {state === 'done' ? 'read again' : 'read your shelf'}
            </Button>
          ) : null}
          {state === 'running' ? (
            <Button onClick={() => void pause()}>pause</Button>
          ) : null}
          {state === 'paused' ? (
            <Button onClick={() => void resume()}>resume</Button>
          ) : null}
        </div>
      </div>

      {isActive || state === 'done' ? (
        <div className="mt-6 flex flex-col gap-3">
          <Meter value={done} max={total} ariaLabel="reading progress" />
          <Label tone="soft">
            {state === 'done'
              ? `read · ${done} of ${total}`
              : `reading ${done} of ${total}${
                  progress?.currentTitle ? ` · ${progress.currentTitle}` : ''
                }${state === 'paused' ? ' · paused' : ''}`}
          </Label>
        </div>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="mt-4 rounded-[12px] border-l-2 border-clay bg-clay/8 py-2 pl-3 pr-3 font-body text-[16px] leading-[1.6] text-ink"
        >
          {error}
        </p>
      ) : null}
    </Panel>
  )
}
