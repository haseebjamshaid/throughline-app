import type { SVGProps } from 'react'

/**
 * Empty-state vignette for search: a quiet wide view of layered hills under a
 * low warm sun with a few birds — open, waiting, calm. Far layers paler, near
 * layers richer.
 */
export function HillsWithSun(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 220 140" fill="none" role="img" aria-hidden {...props}>
      {/* low sun */}
      <circle cx="150" cy="48" r="24" fill="#d8a85a" opacity="0.85" />
      <circle cx="150" cy="48" r="24" fill="#cba35f" opacity="0.25" />

      {/* far ridge — sand */}
      <path d="M0 86 C40 70 80 78 120 70 C160 62 190 74 220 68 L220 140 L0 140 Z" fill="#d8c8a8" />
      {/* mid ridge — terracotta */}
      <path d="M0 102 C50 90 96 96 140 90 C178 85 200 94 220 90 L220 140 L0 140 Z" fill="#c67b5c" opacity="0.92" />
      {/* near ridge — clay */}
      <path d="M0 120 C56 110 110 116 160 112 C190 109 208 115 220 112 L220 140 L0 140 Z" fill="#a9683f" />

      {/* two birds, far off */}
      <path d="M58 40 C62 37 64 37 67 40 C70 37 72 37 76 40" stroke="#8c7b64" strokeWidth="1.2" strokeLinecap="round" fill="none" opacity="0.7" />
      <path d="M84 32 C87 30 89 30 91 32 C93 30 95 30 98 32" stroke="#8c7b64" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.55" />
    </svg>
  )
}
