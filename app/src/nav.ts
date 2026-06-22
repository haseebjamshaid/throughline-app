/** Single source of truth for the left-rail navigation and routing. */

export interface NavItem {
  /** Route path. */
  path: string
  /** Label shown in the rail and as the screen heading. */
  label: string
}

/** Primary navigation, top of the rail. Order is intentional. */
export const NAV_ITEMS: readonly NavItem[] = [
  { path: '/vault', label: 'vault' },
  { path: '/profile', label: 'profile' },
  { path: '/thread', label: 'the thread' },
  { path: '/fit-check', label: 'fit check' },
  { path: '/vibe-search', label: 'vibe search' },
] as const

/**
 * The capture action lives apart, pinned to the bottom of the rail. Capture is
 * part of the Vault screen, so this routes there (and the rail highlights it
 * while on /vault).
 */
export const CAPTURE_ITEM: NavItem = { path: '/vault', label: 'add to your shelf' }

/** Where the app lands by default — the heart. */
export const DEFAULT_ROUTE = '/thread'
