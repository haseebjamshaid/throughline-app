import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { getProfile } from '../lib/api'
import { DEFAULT_ROUTE } from '../nav'
import { isOnboarded, markOnboarded } from './onboarding'

/**
 * The index gate. Decides where the very first paint goes: returning users (the
 * local onboarded flag, or an existing profile on the backend) drop straight
 * into the heart; everyone else is walked through the guided first run. Renders
 * nothing during the one-shot profile probe to avoid a flash of the wrong
 * screen — the probe is a single fast local call.
 */
export function Landing() {
  const [target, setTarget] = useState<string | null>(null)

  useEffect(() => {
    if (isOnboarded()) {
      setTarget(DEFAULT_ROUTE)
      return
    }
    let mounted = true
    const probe = async (): Promise<void> => {
      const profile = await getProfile()
      if (!mounted) return
      if (profile) {
        // Already has a portrait → treat as onboarded, skip the walk.
        markOnboarded()
        setTarget(DEFAULT_ROUTE)
      } else {
        setTarget('/welcome')
      }
    }
    void probe()
    return () => {
      mounted = false
    }
  }, [])

  if (target === null) return null
  return <Navigate to={target} replace />
}
