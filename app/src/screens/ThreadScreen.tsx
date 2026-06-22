import { Bell } from '@phosphor-icons/react'
import { useThread } from '../lib/appState'
import { Page } from './Page'
import { OfflineNotice } from './OfflineNotice'
import { RestingState } from './thread/RestingState'
import { PullingState } from './thread/PullingState'
import { TurnFlow } from './thread/TurnFlow'
import { ClosedState } from './thread/ClosedState'

/**
 * The thread — the heart of throughline. You say the stuck thing in plain words;
 * the library pulls one question, one connection from your own shelf, and one
 * next step onto a single glowing plate. Make it smaller, swap it, or mark it
 * done to close the loop. Calm, lowercase, spare — a tool, not a friend.
 */
export function ThreadScreen() {
  const {
    state,
    turn,
    isBusy,
    error,
    pull,
    askDifferent,
    askSmaller,
    markDone,
    reset,
  } = useThread()

  return (
    <Page title="the thread" eyebrow="throughline" aside={<NudgesPill />}>
      {state === 'offline' ? (
        <OfflineNotice />
      ) : state === 'pulling' ? (
        <PullingState />
      ) : state === 'closed' ? (
        <ClosedState onNewThread={reset} />
      ) : state === 'pulled' && turn ? (
        <TurnFlow
          turn={turn}
          isBusy={isBusy}
          error={error}
          onDidIt={() => void markDone()}
          onSmaller={() => void askSmaller()}
          onDifferent={() => void askDifferent()}
          onNewThread={reset}
        />
      ) : (
        <RestingState
          onPull={(stuck) => void pull(stuck)}
          isBusy={isBusy}
          noVault={state === 'no-vault'}
          error={error}
        />
      )}
    </Page>
  )
}

/**
 * A small, display-only "nudges: rarely" chip in the header — a quiet promise
 * that the thread won't pester. Ambient nudging itself comes later; this is
 * ambient reassurance, not a control.
 */
function NudgesPill() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-sand/40 px-3.5 py-1.5 font-label text-[12px] font-medium lowercase tracking-[0.03em] text-ink-soft">
      <Bell aria-hidden className="h-3.5 w-3.5" />
      nudges: rarely
    </span>
  )
}
