import type { SVGProps } from 'react'

/**
 * Empty-state vignette for the fit check: a simple balance scale, one pan
 * holding a single terracotta leaf, gently tipping — "does it weigh true for
 * you?". Calm, flat, warm.
 */
export function LeafOnScale(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 200 160" fill="none" role="img" aria-hidden {...props}>
      {/* soft hill ground */}
      <path d="M0 134 C50 126 110 130 160 126 C184 124 194 128 200 127 L200 160 L0 160 Z" fill="#d8c8a8" />

      {/* central post */}
      <rect x="97" y="40" width="6" height="92" rx="3" fill="#7a5230" />
      {/* base */}
      <path d="M82 132 C82 128 118 128 118 132 L118 136 L82 136 Z" fill="#a9683f" />

      {/* beam — slightly tipped left (leaf side heavier) */}
      <g transform="rotate(-7 100 44)">
        <rect x="48" y="42" width="104" height="5" rx="2.5" fill="#6f7444" />
        {/* left chains + pan */}
        <line x1="58" y1="46" x2="58" y2="66" stroke="#8c7b64" strokeWidth="1.2" />
        <path d="M46 66 C46 76 70 76 70 66 Z" fill="#c67b5c" />
        {/* right chains + pan */}
        <line x1="142" y1="46" x2="142" y2="62" stroke="#8c7b64" strokeWidth="1.2" />
        <path d="M130 62 C130 72 154 72 154 62 Z" fill="#cba35f" opacity="0.85" />
      </g>

      {/* the leaf resting in the left pan */}
      <path
        d="M52 60 C49 53 51 46 58 43 C61 50 59 57 52 60 Z"
        fill="#c67b5c"
      />
      <path d="M55.5 58 L57 46" stroke="#6f7444" strokeWidth="0.8" opacity="0.7" />

      {/* finial */}
      <circle cx="100" cy="40" r="4.5" fill="#d8a85a" />
    </svg>
  )
}
