import { useId } from 'react'

/** Angular "S" brand mark in the approved violet gradient (references/frontend/03). */
export function BrandMark({ className = 'logo-mark' }: { className?: string }) {
  const id = `bm-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={id} x1="4" y1="3" x2="28" y2="29" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#a96bff" />
          <stop offset=".55" stopColor="#7828ee" />
          <stop offset="1" stopColor="#5521ca" />
        </linearGradient>
      </defs>
      <path d="M25 5.5H12.5L6.5 11.5L12.5 17.5H19.5L25.5 23.5L19.5 29.5" fill="none" stroke={`url(#${id})`} strokeWidth="5.2" strokeLinejoin="round" strokeLinecap="round" />
      <path d="M6.5 26.5H14" fill="none" stroke={`url(#${id})`} strokeWidth="5.2" strokeLinecap="round" opacity=".55" />
    </svg>
  )
}
