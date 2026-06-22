import { Outlet } from 'react-router-dom'
import { NavRail } from './NavRail'
import { Header } from './Header'
import { AppProviders } from '../lib/appState'

/**
 * The cover shell: a fixed left rail + a slim header, the active route in the
 * scrollable main region, and a fixed full-page paper-grain overlay that sits
 * above everything but never intercepts input.
 */
export function AppShell() {
  return (
    <AppProviders>
      <div className="flex h-screen w-screen overflow-hidden bg-paper text-ink">
        <NavRail />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden bg-paper">
            <Outlet />
          </main>
        </div>
        <div className="paper-grain" aria-hidden="true" />
      </div>
    </AppProviders>
  )
}
