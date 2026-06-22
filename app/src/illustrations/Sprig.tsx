import type { SVGProps } from 'react'

/**
 * A small leaf/branch motif — a curved olive stem with a few terracotta and
 * olive leaves. Used for dividers, list bullets, accents, and as a quiet brand
 * accent. Flat fills, soft rounded forms.
 */
export function Sprig(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" role="img" aria-hidden {...props}>
      {/* stem */}
      <path
        d="M12 21 C12 16 11 11 13 6 C14 3.5 16 2.5 17 2"
        stroke="#6f7444"
        strokeWidth="1.4"
        strokeLinecap="round"
        fill="none"
      />
      {/* lower-left leaf — olive */}
      <path
        d="M11.6 14.5 C8.5 14 6.6 12 6.4 9.6 C9 9.6 11.2 11 11.6 14.5 Z"
        fill="#6f7444"
      />
      {/* mid-right leaf — terracotta */}
      <path
        d="M12.6 10.5 C15.8 10.2 17.8 8.2 18 5.8 C15.2 5.8 13 7.4 12.6 10.5 Z"
        fill="#c67b5c"
      />
      {/* upper-left leaf — terracotta, paler */}
      <path
        d="M12.2 7.5 C9.6 7.2 8 5.6 7.9 3.6 C10.1 3.6 11.9 4.8 12.2 7.5 Z"
        fill="#c67b5c"
        opacity="0.8"
      />
    </svg>
  )
}
