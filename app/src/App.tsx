import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './shell/AppShell'
import { DEFAULT_ROUTE } from './nav'
import { Landing } from './onboarding/Landing'
import { OnboardingFlow } from './onboarding/OnboardingFlow'
import { VaultScreen } from './screens/vault/VaultScreen'
import { SearchScreen } from './screens/search/SearchScreen'
import { ThreadScreen } from './screens/ThreadScreen'
import { ProfileScreen } from './screens/ProfileScreen'
import { FitCheckScreen } from './screens/FitCheckScreen'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* First-run gate + guided walk live OUTSIDE the app shell (no nav rail). */}
        <Route index element={<Landing />} />
        <Route path="/welcome" element={<OnboardingFlow />} />
        <Route element={<AppShell />}>
          <Route path="/vault" element={<VaultScreen />} />
          <Route path="/vibe-search" element={<SearchScreen />} />
          <Route path="/thread" element={<ThreadScreen />} />
          <Route path="/profile" element={<ProfileScreen />} />
          <Route path="/fit-check" element={<FitCheckScreen />} />
          <Route path="*" element={<Navigate to={DEFAULT_ROUTE} replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
