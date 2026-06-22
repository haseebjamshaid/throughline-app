/**
 * First-run onboarding persistence — a single local flag so the guided
 * "first ten minutes" shows once per browser. The vault + profile themselves
 * live on disk via the backend; this only remembers that the user has been
 * walked through the door.
 */
const ONBOARDED_KEY = 'throughline:onboarded:v1'

/** True when the guided first-run flow has already been completed/dismissed. */
export function isOnboarded(): boolean {
  try {
    return localStorage.getItem(ONBOARDED_KEY) === 'true'
  } catch {
    // Private mode / storage disabled — treat as not-onboarded (no crash).
    return false
  }
}

/** Remember that onboarding is done, so the app lands in the heart next time. */
export function markOnboarded(): void {
  try {
    localStorage.setItem(ONBOARDED_KEY, 'true')
  } catch {
    // Storage unavailable — onboarding simply shows again next time. Harmless.
  }
}
