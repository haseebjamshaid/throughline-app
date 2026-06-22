import type { SVGProps } from 'react'

/**
 * A row of simple pine silhouettes (stacked triangles) standing on a foreground
 * band, in olive and warm brown. Flat, vintage, layered — a calmer near band of
 * darker pines in front of a paler receding row behind. No gradients.
 */
export function PineRidge(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 320 120" fill="none" role="img" aria-hidden {...props}>
      {/* far, paler pines */}
      <g fill="#8c8a5e" opacity="0.7">
        <Pine x={36} y={86} h={52} w={30} />
        <Pine x={104} y={86} h={44} w={26} />
        <Pine x={196} y={86} h={50} w={30} />
        <Pine x={266} y={86} h={42} w={24} />
      </g>

      {/* near, richer pines */}
      <g fill="#6f7444">
        <Pine x={0} y={96} h={64} w={38} />
        <Pine x={68} y={96} h={56} w={34} />
        <Pine x={140} y={96} h={68} w={40} />
        <Pine x={226} y={96} h={58} w={36} />
        <Pine x={290} y={96} h={50} w={30} />
      </g>

      {/* foreground earth band */}
      <path d="M0 102 C80 96 160 100 240 98 C290 97 312 100 320 99 L320 120 L0 120 Z" fill="#a9683f" />
    </svg>
  )
}

interface PineProps {
  x: number
  y: number
  h: number
  w: number
}

/** A single stacked-triangle pine with a short trunk, drawn from its base. */
function Pine({ x, y, h, w }: PineProps) {
  const half = w / 2
  const tiers = 3
  const tierH = h / (tiers + 0.4)
  const layers = Array.from({ length: tiers }, (_, i) => {
    const top = y - h + i * tierH * 0.9
    const spread = half * (0.55 + (i / tiers) * 0.45)
    const baseY = y - h + (i + 1.1) * tierH
    return `M ${x - spread} ${baseY} Q ${x} ${baseY - tierH * 0.3} ${x + spread} ${baseY} L ${x} ${top} Z`
  }).join(' ')
  return (
    <g>
      <rect x={x - 2.2} y={y - tierH * 0.5} width="4.4" height={tierH * 0.6} rx="1.5" fill="#7a5230" />
      <path d={layers} />
    </g>
  )
}
