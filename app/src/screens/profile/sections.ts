import type { ProfileSection } from '../../lib/api'

/** The two calm views of the portrait. */
export type ProfileView = 'creative' | 'deeper'

/** A lowercase, warm title for each section heading. */
export const SECTION_TITLE: Record<ProfileSection, string> = {
  mood: 'mood',
  light: 'light',
  framing: 'framing',
  subjects: 'subjects',
  dos: "do's",
  donts: "don'ts",
  themes: 'themes',
  ambitions: 'ambitions',
  threads: 'threads',
}

/** The "creative slice" view — the surface texture of your taste. */
export const CREATIVE_SECTIONS: readonly ProfileSection[] = [
  'mood',
  'light',
  'framing',
  'subjects',
  'dos',
  'donts',
]

/** The "deeper threads" view — what runs underneath. */
export const DEEPER_SECTIONS: readonly ProfileSection[] = [
  'themes',
  'ambitions',
  'threads',
]

/** Sections rendered as soft pills rather than serif lines (e.g. mood). */
export const PILL_SECTIONS: ReadonlySet<ProfileSection> = new Set(['mood'])
