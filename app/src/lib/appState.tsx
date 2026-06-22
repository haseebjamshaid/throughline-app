import { createContext, useContext, type Context, type ReactNode } from 'react'
import { useVault as useVaultHook, type UseVaultResult } from './useVault'
import { useProfile as useProfileHook, type UseProfileResult } from './useProfile'
import { useThread as useThreadHook, type UseThreadResult } from './useThread'
import { useFit as useFitHook, type UseFitResult } from './useFit'
import { useIntake as useIntakeHook, type UseIntakeResult } from './useIntake'
import { useSearch as useSearchHook, type UseSearchResult } from './useSearch'

/*
  App-wide state, instantiated ONCE by <AppProviders> (mounted in the AppShell,
  above the router outlet). Because the provider outlives screen unmount/remount,
  in-flight work — a profile redraw, a thread pull, a fit check, an intake run, a
  search — keeps its busy state and lands its result even when you switch tabs
  mid-flight. Screens import the hooks BELOW (the shared, context-backed
  versions), never the raw ./useX hooks directly — otherwise each visit would
  spin up a fresh instance and forget the work in progress (re-enabling a button
  whose request is still running). Onboarding lives outside this shell and keeps
  its own raw-hook instances on purpose.
*/

const VaultContext = createContext<UseVaultResult | null>(null)
const ProfileContext = createContext<UseProfileResult | null>(null)
const ThreadContext = createContext<UseThreadResult | null>(null)
const FitContext = createContext<UseFitResult | null>(null)
const IntakeContext = createContext<UseIntakeResult | null>(null)
const SearchContext = createContext<UseSearchResult | null>(null)

export function AppProviders({ children }: { children: ReactNode }) {
  const vault = useVaultHook()
  const profile = useProfileHook()
  const thread = useThreadHook()
  const fit = useFitHook()
  const intake = useIntakeHook()
  const search = useSearchHook()
  return (
    <VaultContext.Provider value={vault}>
      <ProfileContext.Provider value={profile}>
        <ThreadContext.Provider value={thread}>
          <FitContext.Provider value={fit}>
            <IntakeContext.Provider value={intake}>
              <SearchContext.Provider value={search}>{children}</SearchContext.Provider>
            </IntakeContext.Provider>
          </FitContext.Provider>
        </ThreadContext.Provider>
      </ProfileContext.Provider>
    </VaultContext.Provider>
  )
}

function useShared<T>(context: Context<T | null>, name: string): T {
  const value = useContext(context)
  if (value === null) {
    throw new Error(`${name} must be used within <AppProviders>`)
  }
  return value
}

export const useVault = (): UseVaultResult => useShared(VaultContext, 'useVault')
export const useProfile = (): UseProfileResult => useShared(ProfileContext, 'useProfile')
export const useThread = (): UseThreadResult => useShared(ThreadContext, 'useThread')
export const useFit = (): UseFitResult => useShared(FitContext, 'useFit')
export const useIntake = (): UseIntakeResult => useShared(IntakeContext, 'useIntake')
export const useSearch = (): UseSearchResult => useShared(SearchContext, 'useSearch')
