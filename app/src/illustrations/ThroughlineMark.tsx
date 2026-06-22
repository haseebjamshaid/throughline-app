import type { SVGProps } from 'react'

/**
 * The brand mark — a refined little roundel emblem: a low sun rising over a
 * single curving path between two soft hill shoulders, ringed by a thin warm
 * keyline. Replaces the plain dot next to "throughline". Reads at small sizes.
 */
export function ThroughlineMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 36 36" fill="none" role="img" aria-hidden {...props}>
      {/* roundel field + ring */}
      <circle cx="18" cy="18" r="16.5" fill="#f7f0df" stroke="#cba35f" strokeWidth="1.2" />
      <clipPath id="tl-mark-clip">
        <circle cx="18" cy="18" r="16.5" />
      </clipPath>

      <g clipPath="url(#tl-mark-clip)">
        {/* low sun */}
        <circle cx="18" cy="15" r="5.4" fill="#d8a85a" />
        {/* far hill shoulders — terracotta */}
        <path d="M0 24 C8 20 14 22 18 21 C24 20 30 23 36 21 L36 36 L0 36 Z" fill="#c67b5c" />
        {/* near hill — olive */}
        <path d="M0 30 C10 27 16 29 22 28 C28 27 33 29 36 28 L36 36 L0 36 Z" fill="#6f7444" />
        {/* the throughline path */}
        <path
          d="M14 36 C13 31 21 30 20 25 C19.4 21.6 16 21 18 17"
          stroke="#b5651d"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />
      </g>
    </svg>
  )
}
