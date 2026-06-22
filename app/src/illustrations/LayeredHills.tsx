import type { SVGProps } from 'react'

/**
 * The signature backdrop — four overlapping hill layers receding into a calm
 * cream sky with a low warm-gold sun. Far layers are paler/desaturated (sand),
 * near layers are richer (clay → olive), giving atmospheric depth like a faded
 * risograph nature print. Soft rounded ridges, flat fills, no gradients.
 *
 * Used faintly behind headers and, larger, inside empty states. The host
 * controls opacity via className.
 */
export function LayeredHills(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 480 220"
      fill="none"
      role="img"
      aria-hidden
      preserveAspectRatio="xMidYMax slice"
      {...props}
    >
      {/* calm cream sky */}
      <rect width="480" height="220" fill="#efe6d0" />

      {/* low warm-gold sun, sitting just above the far ridge */}
      <circle cx="356" cy="96" r="30" fill="#d8a85a" opacity="0.9" />
      <circle cx="356" cy="96" r="30" fill="#cba35f" opacity="0.25" />

      {/* far ridge — palest, most desaturated (sand) */}
      <path
        d="M0 150 C70 120 120 132 180 122 C250 110 300 130 360 120 C420 110 450 128 480 120 L480 220 L0 220 Z"
        fill="#d8c8a8"
      />

      {/* mid-far ridge — terracotta, softened */}
      <path
        d="M0 168 C60 150 110 158 165 150 C235 140 295 162 355 152 C410 144 450 160 480 150 L480 220 L0 220 Z"
        fill="#c67b5c"
        opacity="0.92"
      />

      {/* mid-near ridge — clay, richer */}
      <path
        d="M0 188 C55 176 105 182 160 175 C228 166 290 184 350 176 C405 169 450 182 480 175 L480 220 L0 220 Z"
        fill="#a9683f"
      />

      {/* nearest band — olive foreground */}
      <path
        d="M0 206 C70 198 130 202 200 198 C280 193 340 204 400 200 C440 197 462 203 480 200 L480 220 L0 220 Z"
        fill="#6f7444"
      />
    </svg>
  )
}
