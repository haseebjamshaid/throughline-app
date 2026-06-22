import type { ItemType } from './api'

/**
 * A short lowercase type-label for each item type. On-brand: we prefer quiet
 * lowercase text labels over icons or emoji throughout the cover UI.
 */
interface TypeMeta {
  /** Lowercase tag shown on cover plates, e.g. `a film you love`. */
  label: string
  /** Terse lowercase word for dropdowns / pills, e.g. `film`. */
  short: string
}

/** Per-type presentation. `note` is the fallback for unknown types. */
export const TYPE_META: Record<ItemType, TypeMeta> = {
  movie: { label: 'a film you love', short: 'film' },
  song: { label: 'a song you keep', short: 'song' },
  book: { label: 'a book you hold', short: 'book' },
  quote: { label: 'a quote you carry', short: 'quote' },
  ambition: { label: 'an ambition', short: 'ambition' },
  fear: { label: 'a fear', short: 'fear' },
  experience: { label: 'an experience', short: 'experience' },
  journal: { label: 'a journal note', short: 'journal' },
  image: { label: 'an image', short: 'image' },
  note: { label: 'a note', short: 'note' },
}

/** Types offered in the quick-capture dropdown, in a deliberate order. */
export const CAPTURE_TYPES: readonly ItemType[] = [
  'movie',
  'song',
  'book',
  'quote',
  'ambition',
  'fear',
  'experience',
  'journal',
] as const

/** One filter pill: a label and the predicate that selects items for it. */
export interface TypeFilter {
  key: string
  label: string
  /** Item types this pill matches; `null` means "all". */
  types: readonly ItemType[] | null
}

/**
 * The horizontal filter row above the item list. `Self` is a pseudo-filter
 * handled separately (by `is_self`), so it carries an empty type list and is
 * recognised by its key.
 */
export const VAULT_FILTERS: readonly TypeFilter[] = [
  { key: 'all', label: 'all', types: null },
  { key: 'movie', label: 'films', types: ['movie'] },
  { key: 'song', label: 'songs', types: ['song'] },
  { key: 'book', label: 'books', types: ['book'] },
  { key: 'quote', label: 'quotes', types: ['quote'] },
  { key: 'self', label: 'self', types: [] },
  { key: 'image', label: 'images', types: ['image'] },
] as const

/** Types offered as filter pills on the search screen. */
export const SEARCH_FILTER_TYPES: readonly ItemType[] = [
  'movie',
  'song',
  'book',
  'quote',
  'journal',
] as const
