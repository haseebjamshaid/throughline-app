import type { SVGProps } from 'react'

/**
 * Vignette for the thread: a single tree on a rise at dawn, a large low sun
 * behind it, layered hills beyond. The quiet, hopeful "one place to stand"
 * image. Warm, flat, layered.
 */
export function LoneTreeAtDawn(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 200 150" fill="none" role="img" aria-hidden {...props}>
      {/* big low dawn sun */}
      <circle cx="100" cy="74" r="40" fill="#d8a85a" opacity="0.8" />
      <circle cx="100" cy="74" r="40" fill="#cba35f" opacity="0.2" />

      {/* far hills — sand */}
      <path d="M0 104 C40 92 84 98 120 92 C158 86 184 96 200 92 L200 150 L0 150 Z" fill="#d8c8a8" />
      {/* near rise — clay */}
      <path d="M0 124 C50 112 96 118 130 116 C166 114 186 120 200 118 L200 150 L0 150 Z" fill="#a9683f" />

      {/* the lone tree on the rise */}
      <rect x="97" y="78" width="6" height="44" rx="3" fill="#5e4326" />
      {/* a few soft branches */}
      <path d="M100 96 C92 90 88 86 86 80 M100 100 C108 94 112 90 114 84 M100 90 C95 84 93 80 92 74"
        stroke="#5e4326" strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* layered canopy — olive */}
      <circle cx="100" cy="68" r="22" fill="#6f7444" />
      <circle cx="86" cy="76" r="14" fill="#6f7444" opacity="0.92" />
      <circle cx="114" cy="76" r="13" fill="#8c8a5e" opacity="0.85" />
      <circle cx="100" cy="58" r="13" fill="#8c8a5e" opacity="0.8" />
    </svg>
  )
}
