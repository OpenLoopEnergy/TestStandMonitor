import type { ReactNode } from 'react'

/** Vertical divider between header groups (Status / Actions / Pages). */
export function HeaderDivider() {
  return <div className="h-6 w-px bg-black/10 dark:bg-white/10" />
}

/** Labeled cluster of header items — e.g. all the status pills, or all the nav links. */
export function HeaderGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">{label}</span>
      {children}
    </div>
  )
}
