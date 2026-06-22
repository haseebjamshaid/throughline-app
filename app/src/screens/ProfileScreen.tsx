import { useMemo, useState } from 'react'
import { useProfile } from '../lib/appState'
import type { Profile, ProfileClaim, ProfileSection } from '../lib/api'
import { Label } from '../ui'
import { Page } from './Page'
import { OfflineNotice } from './OfflineNotice'
import { EmptyProfile } from './profile/EmptyProfile'
import { GenerationControls } from './profile/GenerationControls'
import { ViewToggle } from './profile/ViewToggle'
import { PaletteRow } from './profile/PaletteRow'
import { ClaimSection } from './profile/ClaimSection'
import {
  CREATIVE_SECTIONS,
  DEEPER_SECTIONS,
  type ProfileView,
} from './profile/sections'

/**
 * Profile — the portrait the library sketches of you from your shelf. Honest,
 * lowercase, warm. A 404 shows the invitation to generate; once drawn, a calm
 * two-view toggle (creative slice / deeper threads) reveals the palette and the
 * claim lines, each pinnable, editable, and deletable with optimistic UI.
 */
export function ProfileScreen() {
  const {
    state,
    profile,
    isGenerating,
    generateError,
    noVault,
    generate,
    applyEdits,
  } = useProfile()
  const [view, setView] = useState<ProfileView>('creative')

  if (state === 'loading') {
    return (
      <Page title="profile" eyebrow="throughline">
        <Label tone="soft">drawing the picture of you…</Label>
      </Page>
    )
  }

  if (state === 'offline') {
    return (
      <Page title="profile" eyebrow="throughline">
        <OfflineNotice />
      </Page>
    )
  }

  if (state === 'empty' || profile === null) {
    return (
      <Page title="profile" eyebrow="throughline">
        <EmptyProfile
          onGenerate={() => void generate()}
          isGenerating={isGenerating}
          noVault={noVault}
          error={generateError}
        />
      </Page>
    )
  }

  return (
    <Page title="profile" eyebrow="throughline">
      <ProfileBody
        profile={profile}
        view={view}
        onChangeView={setView}
        isGenerating={isGenerating}
        error={generateError}
        onPin={(id, pinned) => void applyEdits([{ id, pinned }])}
        onEditText={(id, text) => void applyEdits([{ id, text }])}
        onDelete={(id) => void applyEdits([{ id, deleted: true }])}
      />
    </Page>
  )
}

interface ProfileBodyProps {
  profile: Profile
  view: ProfileView
  onChangeView: (view: ProfileView) => void
  isGenerating: boolean
  error: string | null
  onPin: (id: string, pinned: boolean) => void
  onEditText: (id: string, text: string) => void
  onDelete: (id: string) => void
}

/** The loaded portrait: name + sources, confidence note, view toggle, sections. */
function ProfileBody({
  profile,
  view,
  onChangeView,
  isGenerating,
  error,
  onPin,
  onEditText,
  onDelete,
}: ProfileBodyProps) {
  const bySection = useMemo(() => groupBySection(profile.claims), [profile.claims])
  const sections = view === 'creative' ? CREATIVE_SECTIONS : DEEPER_SECTIONS
  const sourceLabel = `${profile.sourceCount} ${
    profile.sourceCount === 1 ? 'thing' : 'things'
  } read`

  return (
    <div className="flex flex-col gap-9">
      <header className="flex flex-col gap-3">
        {profile.name ? (
          <h3 className="font-display text-[40px] font-medium lowercase leading-[1.05] tracking-[0.005em] text-ink">
            {profile.name}
          </h3>
        ) : null}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <Label tone="soft">{sourceLabel}</Label>
          {profile.confidenceNote ? (
            <p className="font-body text-[16px] italic leading-[1.5] text-ink-soft">
              {profile.confidenceNote}
            </p>
          ) : null}
        </div>
      </header>

      <GenerationControls />

      {isGenerating ? (
        <Label tone="soft">reading your shelf again — the portrait will refresh…</Label>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="rounded-[12px] border-l-2 border-clay bg-clay/8 py-2 pl-3 pr-3 font-body text-[16px] leading-[1.6] text-ink"
        >
          {error}
        </p>
      ) : null}

      <ViewToggle view={view} onChange={onChangeView} />

      {view === 'creative' ? <PaletteRow palette={profile.palette} /> : null}

      <div className="flex flex-col gap-8">
        {sections.map((section) => (
          <ClaimSection
            key={section}
            section={section}
            claims={bySection.get(section) ?? []}
            onPin={onPin}
            onEditText={onEditText}
            onDelete={onDelete}
          />
        ))}
      </div>

      {hasNoClaims(bySection, sections) ? (
        <p className="font-body text-[18px] italic leading-[1.65] text-ink-soft">
          nothing to show in this view yet.
        </p>
      ) : null}
    </div>
  )
}

/** Group claims by their section, preserving order within each section. */
function groupBySection(
  claims: readonly ProfileClaim[],
): Map<ProfileSection, ProfileClaim[]> {
  const map = new Map<ProfileSection, ProfileClaim[]>()
  for (const claim of claims) {
    const bucket = map.get(claim.section)
    if (bucket) bucket.push(claim)
    else map.set(claim.section, [claim])
  }
  return map
}

/** True when none of the visible sections hold any claims. */
function hasNoClaims(
  bySection: Map<ProfileSection, ProfileClaim[]>,
  sections: readonly ProfileSection[],
): boolean {
  return sections.every((section) => (bySection.get(section)?.length ?? 0) === 0)
}
