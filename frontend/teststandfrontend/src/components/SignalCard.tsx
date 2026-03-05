import type { ChartSignal } from '../types/signals'

interface Props {
  label: string
  value: string
  signal?: ChartSignal
  active?: boolean
  onClick?: (signal: ChartSignal) => void
  compact?: boolean
  className?: string
}

export function SignalCard({ label, value, signal, active, onClick, compact, className = '' }: Props) {
  const clickable = Boolean(signal && onClick)

  return (
    <div
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={() => signal && onClick?.(signal)}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && signal) {
          e.preventDefault()
          onClick?.(signal)
        }
      }}
      className={[
        compact
          ? 'flex flex-col px-2 py-1 rounded-md transition-colors'
          : 'flex justify-between items-center px-3 py-2 rounded-lg text-sm transition-colors',
        clickable
          ? 'cursor-pointer hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-red-500'
          : '',
        active
          ? 'bg-red-700/40 border border-red-500'
          : 'bg-white/5 border border-white/10',
        className,
      ].join(' ')}
    >
      <span className="text-white/60 font-medium uppercase tracking-wide text-[11px] leading-none">{label}</span>
      <span className={`font-mono font-bold text-white ${compact ? 'text-sm mt-0.5' : 'text-base'}`}>{value}</span>
    </div>
  )
}
