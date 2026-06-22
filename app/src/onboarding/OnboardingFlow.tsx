import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DEFAULT_ROUTE } from '../nav'
import { ThroughlineMark } from '../illustrations'
import { markOnboarded } from './onboarding'
import { Stepper } from './Stepper'
import { ConnectStep } from './ConnectStep'
import { ReadingStep } from './ReadingStep'
import { RevealStep } from './RevealStep'
import { HandoffStep } from './HandoffStep'

/** The four beats of the guided first run. */
type Step = 'connect' | 'reading' | 'reveal' | 'handoff'

const STEP_INDEX: Record<Step, number> = {
  connect: 0,
  reading: 1,
  reveal: 2,
  handoff: 3,
}

/**
 * The guided "first ten minutes" — a focused, full-bleed walk (no nav rail) from
 * an empty start to the heart: point at a vault, watch it read, meet the first
 * portrait, then pull a first thread. Each beat hands the next what it needs; a
 * quiet "skip for now" or the final handoff marks onboarding done and drops the
 * user into the app. Calm, lowercase, warm — the day-one moment.
 */
export function OnboardingFlow() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('connect')
  const [indexed, setIndexed] = useState<number | null>(null)

  const finish = (to: string): void => {
    markOnboarded()
    navigate(to)
  }

  return (
    <div className="relative min-h-screen w-screen overflow-y-auto bg-paper text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center px-6 py-12">
        <header className="flex flex-col items-center gap-6">
          <span className="flex items-center gap-2">
            <ThroughlineMark aria-hidden className="h-6 w-6" />
            <span className="font-display text-[20px] font-medium lowercase tracking-[0.01em] text-ink">
              throughline
            </span>
          </span>
          <Stepper current={STEP_INDEX[step]} />
        </header>

        <main className="flex flex-1 flex-col justify-center py-10">
          {step === 'connect' ? (
            <ConnectStep
              onConnected={(count) => {
                setIndexed(count)
                setStep('reading')
              }}
            />
          ) : step === 'reading' ? (
            <ReadingStep indexed={indexed} onContinue={() => setStep('reveal')} />
          ) : step === 'reveal' ? (
            <RevealStep onContinue={() => setStep('handoff')} />
          ) : (
            <HandoffStep
              onPullThread={() => finish('/thread')}
              onExplore={() => finish(DEFAULT_ROUTE)}
            />
          )}
        </main>

        <footer className="pt-4">
          {step !== 'handoff' ? (
            <button
              type="button"
              onClick={() => finish(DEFAULT_ROUTE)}
              className="font-label text-[12px] font-medium lowercase tracking-[0.03em] text-ink-soft underline decoration-border underline-offset-2 transition-colors duration-150 hover:text-clay hover:decoration-terracotta"
            >
              skip for now
            </button>
          ) : null}
        </footer>
      </div>
      <div className="paper-grain" aria-hidden="true" />
    </div>
  )
}
