/**
 * Tiny client for the throughline local backend.
 *
 * The backend is local-first (FastAPI on 127.0.0.1:8000) and may simply not be
 * running. Every call therefore degrades gracefully: a network failure is a
 * normal "offline" state, not an exception the UI should crash on.
 */

export const API_BASE = 'http://127.0.0.1:8000'

/** Default request timeout (ms) — the backend is local, so it should be snappy. */
const REQUEST_TIMEOUT_MS = 3000

/** Long timeout (ms) for slow model calls (e.g. profile generation, ~30–60s). */
const GENERATE_TIMEOUT_MS = 120000

/** Shape returned by `GET /health`, as surfaced to the UI. */
export interface HealthStatus {
  ollamaReachable: boolean
  modelsPresent: boolean
}

/** Raw, untrusted JSON shape from the backend before validation. */
interface RawHealth {
  ollama_reachable?: unknown
  models_present?: unknown
}

function asBool(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  // models_present may arrive as a list of model names; non-empty means present.
  if (Array.isArray(value)) return value.length > 0
  return false
}

function parseHealth(raw: RawHealth): HealthStatus {
  return {
    ollamaReachable: asBool(raw.ollama_reachable),
    modelsPresent: asBool(raw.models_present),
  }
}

/**
 * GET a JSON endpoint with a timeout. Throws on non-2xx or network failure so
 * callers can map failure to a graceful state.
 */
async function getJson<T>(path: string): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      throw new Error(`Request to ${path} failed: ${response.status}`)
    }
    return (await response.json()) as T
  } finally {
    clearTimeout(timeout)
  }
}

/**
 * Fetch backend health. Returns `null` when the backend is unreachable so the
 * caller can represent an explicit "offline" state.
 */
export async function fetchHealth(): Promise<HealthStatus | null> {
  try {
    const raw = await getJson<RawHealth>('/health')
    return parseHealth(raw)
  } catch {
    // Backend down / unreachable — this is an expected local-first condition.
    return null
  }
}

/** Role a configured model plays, mirroring the backend `ModelStatus.role`. */
export type ModelRole = 'embed' | 'text' | 'vision' | 'other'

/** On/off status of one configured model, as surfaced to the Models panel. */
export interface ModelStatus {
  name: string
  role: ModelRole
  installed: boolean
  loaded: boolean
  /** Resident VRAM in MB when loaded, else `null`. */
  sizeMb: number | null
}

/** Raw, untrusted `ModelStatus` JSON from the backend before validation. */
interface RawModelStatus {
  name?: unknown
  role?: unknown
  installed?: unknown
  loaded?: unknown
  size_mb?: unknown
}

const MODEL_ROLES: readonly ModelRole[] = ['embed', 'text', 'vision', 'other']

function asRole(value: unknown): ModelRole {
  return MODEL_ROLES.includes(value as ModelRole) ? (value as ModelRole) : 'other'
}

function parseModelStatus(raw: RawModelStatus): ModelStatus {
  return {
    name: typeof raw.name === 'string' ? raw.name : '',
    role: asRole(raw.role),
    installed: raw.installed === true,
    loaded: raw.loaded === true,
    sizeMb: typeof raw.size_mb === 'number' ? raw.size_mb : null,
  }
}

/** POST JSON to a path with a timeout; throws on non-2xx or network failure. */
async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      throw new Error(`Request to ${path} failed: ${response.status}`)
    }
    return (await response.json()) as T
  } finally {
    clearTimeout(timeout)
  }
}

/**
 * Fetch the status of the three configured models. Returns `null` when the
 * backend is unreachable so callers can show an explicit offline state.
 */
export async function getModels(): Promise<ModelStatus[] | null> {
  try {
    const raw = await getJson<RawModelStatus[]>('/models')
    return Array.isArray(raw) ? raw.map(parseModelStatus) : []
  } catch {
    return null
  }
}

/** Load (preload into RAM) a configured model; returns its updated status. */
export async function loadModel(name: string): Promise<ModelStatus> {
  const raw = await postJson<RawModelStatus>('/models/load', { name })
  return parseModelStatus(raw)
}

/** Unload a configured model from RAM; returns its updated status. */
export async function unloadModel(name: string): Promise<ModelStatus> {
  const raw = await postJson<RawModelStatus>('/models/unload', { name })
  return parseModelStatus(raw)
}

/** Unload every currently-loaded model; returns the updated status list. */
export async function unloadAll(): Promise<ModelStatus[]> {
  const raw = await postJson<RawModelStatus[]>('/models/unload-all')
  return Array.isArray(raw) ? raw.map(parseModelStatus) : []
}

/**
 * A request that failed with an HTTP status the UI may want to branch on
 * (e.g. 409 "no vault connected"). Carries the parsed `detail` when present.
 */
export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** True when an error is an {@link ApiError} carrying the given HTTP status. */
export function isApiStatus(error: unknown, status: number): boolean {
  return error instanceof ApiError && error.status === status
}

/**
 * POST JSON and, on failure, throw an {@link ApiError} that preserves the HTTP
 * status and the backend `detail` string. Used by user-initiated actions where
 * the UI must distinguish error kinds (409 vs 503 vs offline) rather than just
 * falling back to an offline state.
 */
async function postJsonOrThrow<T>(
  path: string,
  body?: unknown,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      const detail = await readDetail(response)
      throw new ApiError(response.status, detail)
    }
    return (await response.json()) as T
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error
    // Network failure / abort — surface as a 0-status "offline" ApiError.
    throw new ApiError(0, 'backend offline')
  } finally {
    clearTimeout(timeout)
  }
}

/** PATCH JSON with the same error semantics as {@link postJsonOrThrow}. */
async function patchJsonOrThrow<T>(path: string, body: unknown): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'PATCH',
      signal: controller.signal,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const detail = await readDetail(response)
      throw new ApiError(response.status, detail)
    }
    return (await response.json()) as T
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, 'backend offline')
  } finally {
    clearTimeout(timeout)
  }
}

/** Best-effort extraction of a FastAPI `{detail}` message from a failed body. */
async function readDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // Non-JSON body — fall through to a generic message.
  }
  return `request failed (${response.status})`
}

/** The kind of thing a vault item is — drives the icon + capture dropdown. */
export type ItemType =
  | 'movie'
  | 'song'
  | 'book'
  | 'quote'
  | 'ambition'
  | 'fear'
  | 'experience'
  | 'journal'
  | 'image'
  | 'note'

/** One note/item in the vault, as surfaced to the UI. */
export interface Item {
  id: string
  path: string
  type: ItemType
  title: string
  feeling: string | null
  tags: string[]
  body: string
  contentHash: string
  isSelf: boolean
  locked: boolean
}

interface RawItem {
  id?: unknown
  path?: unknown
  type?: unknown
  title?: unknown
  feeling?: unknown
  tags?: unknown
  body?: unknown
  content_hash?: unknown
  is_self?: unknown
  locked?: unknown
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []
}

function asItemType(value: unknown): ItemType {
  const known: readonly ItemType[] = [
    'movie',
    'song',
    'book',
    'quote',
    'ambition',
    'fear',
    'experience',
    'journal',
    'image',
    'note',
  ]
  return known.includes(value as ItemType) ? (value as ItemType) : 'note'
}

function parseItem(raw: RawItem): Item {
  return {
    id: asString(raw.id),
    path: asString(raw.path),
    type: asItemType(raw.type),
    title: asString(raw.title),
    feeling: typeof raw.feeling === 'string' ? raw.feeling : null,
    tags: asStringArray(raw.tags),
    body: asString(raw.body),
    contentHash: asString(raw.content_hash),
    isSelf: raw.is_self === true,
    locked: raw.locked === true,
  }
}

/** Result of connecting a vault. */
export interface VaultConnection {
  vaultPath: string
  cacheDir: string
  indexed: number
}

interface RawVaultConnection {
  vault_path?: unknown
  cache_dir?: unknown
  indexed?: unknown
}

/**
 * Connect (and index) an Obsidian vault by absolute path. The backend then
 * remembers this vault process-wide. Throws an {@link ApiError} on failure so
 * the connect panel can show why (404 missing path, 503 backend, etc.).
 */
export async function connectVault(path: string): Promise<VaultConnection> {
  const raw = await postJsonOrThrow<RawVaultConnection>('/vault/connect', { path })
  return {
    vaultPath: asString(raw.vault_path),
    cacheDir: asString(raw.cache_dir),
    indexed: typeof raw.indexed === 'number' ? raw.indexed : 0,
  }
}

/**
 * List vault items. Returns `null` when the backend is unreachable, and an
 * empty array when reachable but no vault is connected — both let the caller
 * show the connect panel rather than crashing.
 */
export async function getItems(): Promise<Item[] | null> {
  try {
    const raw = await getJson<RawItem[]>('/vault/items')
    return Array.isArray(raw) ? raw.map(parseItem) : []
  } catch {
    return null
  }
}

/** Fields accepted when capturing a new item. */
export interface CaptureInput {
  type: ItemType
  title: string
  body?: string
  feeling?: string
  tags?: string[]
}

/** Capture a new item (writes a real .md note); returns the created item. */
export async function captureItem(input: CaptureInput): Promise<Item> {
  const raw = await postJsonOrThrow<RawItem>('/vault/capture', input)
  return parseItem(raw)
}

/** Fields that may be edited on an existing item. `body` edits the note prose. */
export interface ItemPatch {
  type?: ItemType
  title?: string
  feeling?: string
  tags?: string[]
  body?: string
}

/** Update an existing item (metadata and/or body); returns the updated item. */
export async function updateItem(id: string, patch: ItemPatch): Promise<Item> {
  const raw = await patchJsonOrThrow<RawItem>(
    `/vault/items/${encodeURIComponent(id)}`,
    patch,
  )
  return parseItem(raw)
}

/** DELETE a path with the same ApiError semantics as {@link postJsonOrThrow}. */
async function deleteOrThrow(path: string): Promise<void> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) {
      const detail = await readDetail(response)
      throw new ApiError(response.status, detail)
    }
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, 'backend offline')
  } finally {
    clearTimeout(timeout)
  }
}

/** Delete a vault item: removes the `.md` file and prunes it from the index. */
export async function deleteItem(id: string): Promise<void> {
  await deleteOrThrow(`/vault/items/${encodeURIComponent(id)}`)
}

/** One ranked search hit, as surfaced to the UI. */
export interface SearchResult {
  itemId: string
  title: string
  path: string
  /** Match strength in 0..1. */
  score: number
  /** Human-readable reason this matched. */
  why: string
}

interface RawSearchResult {
  item_id?: unknown
  title?: unknown
  path?: unknown
  score?: unknown
  why?: unknown
}

function parseSearchResult(raw: RawSearchResult): SearchResult {
  return {
    itemId: asString(raw.item_id),
    title: asString(raw.title),
    path: asString(raw.path),
    score: typeof raw.score === 'number' ? raw.score : 0,
    why: asString(raw.why),
  }
}

/** Parameters for a vibe search. */
export interface SearchInput {
  query: string
  types?: string[]
  inwardOnly?: boolean
  k?: number
}

/**
 * Search the vault by feeling. Throws an {@link ApiError} (e.g. 409 when no
 * vault is connected) so the UI can guide the user to connect first.
 */
export async function search(input: SearchInput): Promise<SearchResult[]> {
  const body: Record<string, unknown> = { query: input.query }
  if (input.types) body.types = input.types
  if (input.inwardOnly !== undefined) body.inward_only = input.inwardOnly
  if (input.k !== undefined) body.k = input.k
  const raw = await postJsonOrThrow<RawSearchResult[]>('/search', body)
  return Array.isArray(raw) ? raw.map(parseSearchResult) : []
}

/** The phase the intake reader is in. */
export type IntakePhase = string

/** Live progress of an intake run, streamed over SSE. */
export interface IntakeProgress {
  done: number
  total: number
  currentTitle: string | null
  phase: IntakePhase
  paused: boolean
}

interface RawIntakeProgress {
  done?: unknown
  total?: unknown
  current_title?: unknown
  phase?: unknown
  paused?: unknown
}

/** Parse one SSE `IntakeProgress` payload, tolerating missing fields. */
export function parseIntakeProgress(raw: RawIntakeProgress): IntakeProgress {
  return {
    done: typeof raw.done === 'number' ? raw.done : 0,
    total: typeof raw.total === 'number' ? raw.total : 0,
    currentTitle: typeof raw.current_title === 'string' ? raw.current_title : null,
    phase: asString(raw.phase),
    paused: raw.paused === true,
  }
}

/* ---------------------------------------------------------------------------
   Profile — the portrait the library sketches of you from your shelf. A slow
   model call generates it; it can then be pinned/edited/deleted claim by claim.
   --------------------------------------------------------------------------- */

/** Which facet of the portrait a claim belongs to. Drives its grouping. */
export type ProfileSection =
  | 'mood'
  | 'light'
  | 'framing'
  | 'subjects'
  | 'dos'
  | 'donts'
  | 'themes'
  | 'ambitions'
  | 'threads'

/** How sure the library is about a single claim. */
export type ProfileConfidence = 'low' | 'medium' | 'high'

/** One line of the portrait — a single observation drawn from the shelf. */
export interface ProfileClaim {
  id: string
  section: ProfileSection
  text: string
  /** Titles/snippets this claim was drawn from; its length is the "because of N things" annotation. */
  examples: string[]
  confidence: ProfileConfidence
  pinned: boolean
}

/** One named colour in the portrait's palette. */
export interface PaletteColor {
  name: string
  hex: string
}

/** The whole portrait, as surfaced to the profile screen. */
export interface Profile {
  name: string
  sourceCount: number
  confidenceNote: string
  palette: PaletteColor[]
  claims: ProfileClaim[]
  /** ISO timestamp of the last generation, or `null` if never generated. */
  generatedAt: string | null
  /** Sampling temperature the portrait was drawn with (0 = deterministic). */
  temperature: number
  /** Sampling seed the portrait was drawn with. */
  seed: number
}

interface RawProfileClaim {
  id?: unknown
  section?: unknown
  text?: unknown
  examples?: unknown
  confidence?: unknown
  pinned?: unknown
}

interface RawPaletteColor {
  name?: unknown
  hex?: unknown
}

interface RawProfile {
  name?: unknown
  source_count?: unknown
  confidence_note?: unknown
  palette?: unknown
  claims?: unknown
  generated_at?: unknown
  temperature?: unknown
  seed?: unknown
}

const PROFILE_SECTIONS: readonly ProfileSection[] = [
  'mood',
  'light',
  'framing',
  'subjects',
  'dos',
  'donts',
  'themes',
  'ambitions',
  'threads',
]

const PROFILE_CONFIDENCES: readonly ProfileConfidence[] = ['low', 'medium', 'high']

function asSection(value: unknown): ProfileSection {
  return PROFILE_SECTIONS.includes(value as ProfileSection)
    ? (value as ProfileSection)
    : 'themes'
}

function asConfidence(value: unknown): ProfileConfidence {
  return PROFILE_CONFIDENCES.includes(value as ProfileConfidence)
    ? (value as ProfileConfidence)
    : 'medium'
}

function parsePaletteColor(raw: RawPaletteColor): PaletteColor {
  return { name: asString(raw.name), hex: asString(raw.hex) }
}

function parseProfileClaim(raw: RawProfileClaim): ProfileClaim {
  return {
    id: asString(raw.id),
    section: asSection(raw.section),
    text: asString(raw.text),
    examples: asStringArray(raw.examples),
    confidence: asConfidence(raw.confidence),
    pinned: raw.pinned === true,
  }
}

function parseProfile(raw: RawProfile): Profile {
  const palette = Array.isArray(raw.palette)
    ? (raw.palette as RawPaletteColor[]).map(parsePaletteColor)
    : []
  const claims = Array.isArray(raw.claims)
    ? (raw.claims as RawProfileClaim[]).map(parseProfileClaim)
    : []
  return {
    name: asString(raw.name),
    sourceCount: typeof raw.source_count === 'number' ? raw.source_count : 0,
    confidenceNote: asString(raw.confidence_note),
    palette,
    claims,
    generatedAt: typeof raw.generated_at === 'string' ? raw.generated_at : null,
    temperature: typeof raw.temperature === 'number' ? raw.temperature : 0,
    seed: typeof raw.seed === 'number' ? raw.seed : 7,
  }
}

/**
 * Fetch the current profile. Returns `null` when none has been generated yet
 * (the backend answers 404) or when it is unreachable — both are normal,
 * non-error states the screen branches on (empty vs offline is told apart by
 * {@link fetchHealth}/items elsewhere; here a 404 simply means "no profile").
 */
export async function getProfile(): Promise<Profile | null> {
  try {
    const raw = await getJson<RawProfile>('/profile')
    return parseProfile(raw)
  } catch {
    // 404 (no profile yet) or network failure — caller shows empty/offline.
    return null
  }
}

/**
 * Generate (or regenerate) the profile from the connected vault. Slow — a model
 * call. Throws an {@link ApiError} so the screen can branch on 409 (no vault
 * connected) versus offline. Uses a long timeout because generation can take
 * 30–60s.
 */
/** Knobs for a profile (re)generation. Omitted fields use the backend defaults. */
export interface GenerateOptions {
  /** Sampling temperature (0–2). 0 = identical every redraw. */
  temperature?: number
  /** Sampling seed — change it for a different take at temperature > 0. */
  seed?: number
  /** Force a redraw even when the vault + knobs are unchanged. */
  force?: boolean
}

export async function generateProfile(opts: GenerateOptions = {}): Promise<Profile> {
  const params = new URLSearchParams()
  if (opts.temperature !== undefined) params.set('temperature', String(opts.temperature))
  if (opts.seed !== undefined) params.set('seed', String(opts.seed))
  if (opts.force) params.set('force', 'true')
  const query = params.toString()
  const raw = await postJsonOrThrow<RawProfile>(
    `/profile/generate${query ? `?${query}` : ''}`,
    undefined,
    GENERATE_TIMEOUT_MS,
  )
  return parseProfile(raw)
}

/** One edit to a single claim: rename, (un)pin, or delete it. */
export interface ProfileEdit {
  id: string
  text?: string
  pinned?: boolean
  deleted?: boolean
}

/**
 * Apply a batch of claim edits and return the updated profile (the source of
 * truth the screen reconciles its optimistic state against). Throws an
 * {@link ApiError} on failure.
 */
export async function patchProfile(edits: ProfileEdit[]): Promise<Profile> {
  const raw = await patchJsonOrThrow<RawProfile>('/profile', { edits })
  return parseProfile(raw)
}

/* ---------------------------------------------------------------------------
   The thread — the heart. You say the stuck thing in plain words; the library
   pulls one question, one connection from your own shelf, and one next step.
   A slow model call (~10–40s), so it uses the long timeout and throws ApiError
   so the screen can tell a 409 (no vault connected) apart from offline.
   --------------------------------------------------------------------------- */

/** A connection the thread found back to one of the user's own kept items. */
export interface ThreadConnection {
  itemId: string
  title: string
  /** The quoted line from the user's own item. */
  quote: string
  /** Why this thread connects to what they're stuck on. */
  why: string
}

/** The size of a next step — `smaller` is the gentler, lower-effort variant. */
export type NextStepSize = 'normal' | 'smaller'

/** The single next step the thread offers — the one warm focal moment. */
export interface NextStep {
  text: string
  size: NextStepSize
}

/** One turn of the thread: the stuck statement, a question, a connection, a step. */
export interface ThreadTurn {
  id: string
  stuck: string
  question: string
  /** A line pulled from the user's own shelf, or `null` when none was found. */
  connection: ThreadConnection | null
  nextStep: NextStep
  /** True once the loop is closed (the user marked the step done). */
  done: boolean
}

interface RawThreadConnection {
  item_id?: unknown
  title?: unknown
  quote?: unknown
  why?: unknown
}

interface RawNextStep {
  text?: unknown
  size?: unknown
}

interface RawThreadTurn {
  id?: unknown
  stuck?: unknown
  question?: unknown
  connection?: unknown
  next_step?: unknown
  done?: unknown
}

const NEXT_STEP_SIZES: readonly NextStepSize[] = ['normal', 'smaller']

function asNextStepSize(value: unknown): NextStepSize {
  return NEXT_STEP_SIZES.includes(value as NextStepSize)
    ? (value as NextStepSize)
    : 'normal'
}

function parseConnection(raw: unknown): ThreadConnection | null {
  if (raw === null || typeof raw !== 'object') return null
  const conn = raw as RawThreadConnection
  return {
    itemId: asString(conn.item_id),
    title: asString(conn.title),
    quote: asString(conn.quote),
    why: asString(conn.why),
  }
}

function parseNextStep(raw: unknown): NextStep {
  const step = (raw && typeof raw === 'object' ? raw : {}) as RawNextStep
  return { text: asString(step.text), size: asNextStepSize(step.size) }
}

function parseThreadTurn(raw: RawThreadTurn): ThreadTurn {
  return {
    id: asString(raw.id),
    stuck: asString(raw.stuck),
    question: asString(raw.question),
    connection: parseConnection(raw.connection),
    nextStep: parseNextStep(raw.next_step),
    done: raw.done === true,
  }
}

/**
 * Pull a thread: say the stuck thing, get back one question, one connection from
 * your own shelf, and one next step. Slow — a model call (~10–40s). Throws an
 * {@link ApiError} so the screen can branch on 409 (no vault connected) vs
 * offline. Uses the long timeout.
 */
export async function pullThread(stuck: string): Promise<ThreadTurn> {
  const raw = await postJsonOrThrow<RawThreadTurn>(
    '/thread',
    { stuck },
    GENERATE_TIMEOUT_MS,
  )
  return parseThreadTurn(raw)
}

/** Ask for a different next step on an existing thread. Slow — a model call. */
export async function threadDifferent(id: string): Promise<ThreadTurn> {
  const raw = await postJsonOrThrow<RawThreadTurn>(
    `/thread/${encodeURIComponent(id)}/different`,
    undefined,
    GENERATE_TIMEOUT_MS,
  )
  return parseThreadTurn(raw)
}

/** Ask for a smaller, gentler next step on an existing thread. Slow. */
export async function threadSmaller(id: string): Promise<ThreadTurn> {
  const raw = await postJsonOrThrow<RawThreadTurn>(
    `/thread/${encodeURIComponent(id)}/smaller`,
    undefined,
    GENERATE_TIMEOUT_MS,
  )
  return parseThreadTurn(raw)
}

/** Mark the step done — close the loop. Returns the turn with `done: true`. */
export async function threadDidIt(id: string): Promise<ThreadTurn> {
  const raw = await postJsonOrThrow<RawThreadTurn>(
    `/thread/${encodeURIComponent(id)}/did-it`,
    undefined,
    GENERATE_TIMEOUT_MS,
  )
  return parseThreadTurn(raw)
}

/** Start reading (intaking) the connected vault. Throws on failure. */
export async function startIntake(): Promise<void> {
  await postJsonOrThrow<unknown>('/intake/start')
}

/** Pause an in-flight intake run. Throws on failure. */
export async function pauseIntake(): Promise<void> {
  await postJsonOrThrow<unknown>('/intake/pause')
}

/** Resume a paused intake run. Throws on failure. */
export async function resumeIntake(): Promise<void> {
  await postJsonOrThrow<unknown>('/intake/resume')
}

/** Absolute URL for the intake progress SSE stream (`EventSource`). */
export const INTAKE_PROGRESS_URL = `${API_BASE}/intake/progress`

/* ---------------------------------------------------------------------------
   Fit check — hold something up against your profile and hear, honestly, how
   *you* it is: a 0–100 closeness score, one verdict, a checklist tied to your
   own profile claims (each with a fix), and the closest things from your shelf.
   A slow model call (~10–40s), so it uses the long timeout and throws ApiError
   so the screen can tell a 409 (no vault / no profile) apart from offline.
   --------------------------------------------------------------------------- */

/** What you can hold up against your profile. */
export type FitKind = 'image' | 'caption' | 'song'

/** One check tied to a real profile claim: did the thing fit that rule? */
export interface FitCheckItem {
  rule: string
  passed: boolean
  /** A concrete nudge toward fit, or `null` when it already fits. */
  fix: string | null
}

/** A nearest match from the user's own shelf. */
export interface FitClosest {
  itemId: string
  title: string
  /** Closeness 0–100 to this item. */
  score: number
}

/** The whole answer to "how me is this?" */
export interface FitResult {
  /** Closeness to the centre of your taste, 0–100. */
  score: number
  verdict: string
  checks: FitCheckItem[]
  closest: FitClosest[]
  kind: string
}

interface RawFitCheckItem {
  rule?: unknown
  passed?: unknown
  fix?: unknown
}

interface RawFitClosest {
  item_id?: unknown
  title?: unknown
  score?: unknown
}

interface RawFitResult {
  score?: unknown
  verdict?: unknown
  checks?: unknown
  closest?: unknown
  kind?: unknown
}

function parseFitCheckItem(raw: RawFitCheckItem): FitCheckItem {
  return {
    rule: asString(raw.rule),
    passed: raw.passed === true,
    fix: typeof raw.fix === 'string' && raw.fix.trim() ? raw.fix : null,
  }
}

function parseFitClosest(raw: RawFitClosest): FitClosest {
  return {
    itemId: asString(raw.item_id),
    title: asString(raw.title),
    score: typeof raw.score === 'number' ? raw.score : 0,
  }
}

function parseFitResult(raw: RawFitResult): FitResult {
  return {
    score: typeof raw.score === 'number' ? raw.score : 0,
    verdict: asString(raw.verdict),
    checks: Array.isArray(raw.checks)
      ? (raw.checks as RawFitCheckItem[]).map(parseFitCheckItem)
      : [],
    closest: Array.isArray(raw.closest)
      ? (raw.closest as RawFitClosest[]).map(parseFitClosest)
      : [],
    kind: asString(raw.kind),
  }
}

/**
 * POST multipart form-data with the same ApiError semantics as
 * {@link postJsonOrThrow}. The browser sets the multipart boundary, so no
 * Content-Type header is supplied.
 */
async function postFormOrThrow<T>(
  path: string,
  form: FormData,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      body: form,
    })
    if (!response.ok) {
      const detail = await readDetail(response)
      throw new ApiError(response.status, detail)
    }
    return (await response.json()) as T
  } catch (error: unknown) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, 'backend offline')
  } finally {
    clearTimeout(timeout)
  }
}

/** What you're holding up: a caption/song text, or an image file. */
export interface FitInput {
  kind: FitKind
  text?: string
  image?: File
}

/**
 * Check the fit of one thing against your profile. Slow — a model call (and a
 * vision pass first for images). Throws an {@link ApiError} so the screen can
 * branch on 409 (no vault / no profile) versus offline.
 */
export async function postFit(input: FitInput): Promise<FitResult> {
  const form = new FormData()
  form.append('kind', input.kind)
  if (input.text) form.append('text', input.text)
  if (input.image) form.append('image', input.image)
  const raw = await postFormOrThrow<RawFitResult>('/fit', form, GENERATE_TIMEOUT_MS)
  return parseFitResult(raw)
}

/**
 * Tell fit a rule doesn't define you ("that's me on purpose"); returns the
 * updated list of disagreed rules. Best-effort — the screen hides the check
 * locally regardless.
 */
export async function postFitDisagree(rule: string): Promise<string[]> {
  const raw = await postJsonOrThrow<{ disagreed?: unknown }>('/fit/disagree', { rule })
  return asStringArray(raw.disagreed)
}

/** One candidate ranked by closeness to your taste (the fast batch lane). */
export interface RankedCandidate {
  text: string
  score: number
  closestTitle: string
  closestId: string
}

interface RawRankedCandidate {
  text?: unknown
  score?: unknown
  closest_title?: unknown
  closest_id?: unknown
}

function parseRanked(raw: RawRankedCandidate): RankedCandidate {
  return {
    text: asString(raw.text),
    score: typeof raw.score === 'number' ? raw.score : 0,
    closestTitle: asString(raw.closest_title),
    closestId: asString(raw.closest_id),
  }
}

/**
 * Rank several candidates by closeness to your taste. Fast — embedding-only, no
 * reasoning pass — so a handful ranks near-instantly. Throws an {@link ApiError}
 * on 409 (no vault) versus offline.
 */
export async function postFitBatch(
  kind: FitKind,
  items: string[],
): Promise<RankedCandidate[]> {
  const raw = await postJsonOrThrow<RawRankedCandidate[]>(
    '/fit/batch',
    { kind, items },
    GENERATE_TIMEOUT_MS,
  )
  return Array.isArray(raw) ? raw.map(parseRanked) : []
}
