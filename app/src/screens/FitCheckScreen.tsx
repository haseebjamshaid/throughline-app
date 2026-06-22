import { Scales } from '@phosphor-icons/react'
import { useFit } from '../lib/appState'
import { Page } from './Page'
import { OfflineNotice } from './OfflineNotice'
import { FitInputForm } from './fit/FitInputForm'
import { CheckingState } from './fit/CheckingState'
import { FitResultView } from './fit/FitResultView'

/**
 * Fit Check — the honest mirror. Hold something up (a caption, a song, an image)
 * and the library weighs it against the picture it drew of you: one closeness
 * score, one honest verdict, a checklist tied to your own profile claims, and
 * the closest things from your own shelf. Drift is honest, not failure — you can
 * always say "that's me on purpose". Calm, lowercase, warm.
 */
export function FitCheckScreen() {
  const { state, result, isBusy, error, check, disagree, reset } = useFit()

  return (
    <Page title="fit check" eyebrow="throughline" aside={<HonestPill />}>
      {state === 'offline' ? (
        <OfflineNotice />
      ) : state === 'checking' ? (
        <CheckingState />
      ) : state === 'checked' && result ? (
        <FitResultView
          result={result}
          onDisagree={(rule) => void disagree(rule)}
          onReset={reset}
        />
      ) : (
        <FitInputForm
          onCheck={(input) => void check(input)}
          isBusy={isBusy}
          noVault={state === 'no-vault'}
          noProfile={state === 'no-profile'}
          error={error}
        />
      )}
    </Page>
  )
}

/**
 * A small, display-only "honest, not flattering" chip in the header — a quiet
 * promise that fit check tells the truth, not what you want to hear.
 */
function HonestPill() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-sand/40 px-3.5 py-1.5 font-label text-[12px] font-medium lowercase tracking-[0.03em] text-ink-soft">
      <Scales aria-hidden className="h-3.5 w-3.5" />
      honest, not flattering
    </span>
  )
}
