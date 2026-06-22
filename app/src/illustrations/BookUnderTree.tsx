import type { SVGProps } from 'react'

/**
 * Empty-state vignette for the profile: an open book resting under a single
 * round-canopied tree on a soft hill, a low sun behind. Charming, calm, layered.
 */
export function BookUnderTree(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 200 160" fill="none" role="img" aria-hidden {...props}>
      {/* low sun */}
      <circle cx="150" cy="50" r="22" fill="#d8a85a" opacity="0.85" />

      {/* far hill */}
      <path d="M0 118 C40 104 90 110 130 104 C170 99 188 108 200 104 L200 160 L0 160 Z" fill="#d8c8a8" />
      {/* near hill */}
      <path d="M0 132 C50 122 100 128 150 124 C180 121 192 126 200 124 L200 160 L0 160 Z" fill="#c67b5c" opacity="0.9" />

      {/* tree trunk */}
      <rect x="62" y="78" width="7" height="44" rx="3" fill="#7a5230" />
      {/* round canopy — layered olive */}
      <circle cx="65" cy="62" r="30" fill="#6f7444" />
      <circle cx="50" cy="70" r="20" fill="#6f7444" opacity="0.9" />
      <circle cx="82" cy="70" r="18" fill="#8c8a5e" opacity="0.85" />

      {/* open book on the grass */}
      <path d="M96 132 L122 126 L122 140 L96 144 Z" fill="#f7f0df" stroke="#a9683f" strokeWidth="1.2" />
      <path d="M148 132 L122 126 L122 140 L148 144 Z" fill="#efe6d0" stroke="#a9683f" strokeWidth="1.2" />
      <path d="M122 126 L122 140" stroke="#a9683f" strokeWidth="1.2" />
      {/* faint text lines */}
      <path d="M102 132 L116 129 M102 136 L116 133" stroke="#8c7b64" strokeWidth="0.8" opacity="0.6" />
      <path d="M128 129 L142 132 M128 133 L142 136" stroke="#8c7b64" strokeWidth="0.8" opacity="0.6" />
    </svg>
  )
}
