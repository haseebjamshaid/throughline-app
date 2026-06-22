import type { SVGProps } from 'react'

/**
 * The "way through" — a terracotta path curving up through soft layered hills
 * toward a small warm sun. The narrative image for the thread: a single route
 * that recedes into calm distance. Far hills paler, near hills richer.
 */
export function WindingPath(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 240 220"
      fill="none"
      role="img"
      aria-hidden
      preserveAspectRatio="xMidYMid meet"
      {...props}
    >
      {/* small sun near the horizon */}
      <circle cx="158" cy="44" r="18" fill="#d8a85a" opacity="0.9" />
      <circle cx="158" cy="44" r="18" fill="#cba35f" opacity="0.3" />

      {/* far hills — palest sand */}
      <path d="M0 80 C50 64 90 72 130 66 C180 58 210 70 240 64 L240 220 L0 220 Z" fill="#d8c8a8" />
      {/* mid hills — terracotta */}
      <path d="M0 108 C50 96 100 102 150 94 C190 88 215 98 240 92 L240 220 L0 220 Z" fill="#c67b5c" opacity="0.9" />
      {/* near hills — clay */}
      <path d="M0 150 C60 138 110 146 160 140 C200 135 222 144 240 140 L240 220 L0 220 Z" fill="#a9683f" />

      {/* the path — a terracotta ribbon narrowing as it climbs toward the sun */}
      <path
        d="M96 220 C92 196 130 184 128 162 C126 142 96 138 104 116 C110 98 142 96 146 76 C148 64 150 56 154 50
           L162 52 C158 60 158 68 156 78 C152 100 122 104 118 120 C112 140 144 144 142 164 C140 188 112 198 116 220 Z"
        fill="#b5651d"
      />
      {/* dashed centre line, paler — the sense of a trodden way */}
      <path
        d="M106 214 C102 192 134 182 132 162 C130 142 102 138 110 116 C116 100 144 96 148 78 C150 66 152 58 155 52"
        stroke="#efe6d0"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeDasharray="2 8"
        fill="none"
        opacity="0.65"
      />
    </svg>
  )
}
