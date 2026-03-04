import type { LogRow } from '../types/signals'

interface Props {
  rows: LogRow[]
  inputFactor: number
}

function scale(v: number | null, factor: number) {
  return v == null ? '—' : (v * factor).toFixed(2)
}

export function DataTable({ rows, inputFactor }: Props) {
  if (rows.length === 0) {
    return (
      <p className="text-gray-500 text-sm text-center py-6">
        No data yet — table populates when Trending is active.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left text-gray-300 border-collapse">
        <thead>
          <tr className="bg-white/10 text-gray-400 uppercase tracking-wide">
            {['Date','Time','S1','SP','TP%','Cycle','Cyc Timer','LC Set','LC Reg','Step',
              'F1','F2','F3','T1','T3','P1','P2','P3','P4','P5','Theo Flow','Eff%'].map(h => (
              <th key={h} className="px-2 py-2 whitespace-nowrap border-b border-white/10">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const s1 = row.S1 ?? 0
            const f1Raw = row.F1 ?? 0
            const f1 = f1Raw * 0.01
            const theoFlow = inputFactor > 0 ? (s1 * inputFactor) / 231 : 0
            const eff = theoFlow > 0 ? (f1 / theoFlow) * 100 : 0

            return (
              <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                <td className="px-2 py-1.5">{row.Date}</td>
                <td className="px-2 py-1.5">{row.Time}</td>
                <td className="px-2 py-1.5">{row.S1 ?? '—'}</td>
                <td className="px-2 py-1.5">{row.SP ?? '—'}</td>
                <td className="px-2 py-1.5">{row.TP != null ? ((row.TP / 10.23)).toFixed(1) : '—'}</td>
                <td className="px-2 py-1.5">{row.Cycle ?? '—'}</td>
                <td className="px-2 py-1.5">{row['Cycle Timer'] != null ? (row['Cycle Timer'] / 100).toFixed(2) : '—'}</td>
                <td className="px-2 py-1.5">{row.LCSetpoint ?? '—'}</td>
                <td className="px-2 py-1.5">{row['LC Regulate'] ?? '—'}</td>
                <td className="px-2 py-1.5 whitespace-nowrap">{row.Step ?? '—'}</td>
                <td className="px-2 py-1.5">{scale(row.F1, 0.01)}</td>
                <td className="px-2 py-1.5">{scale(row.F2, 0.01)}</td>
                <td className="px-2 py-1.5">{scale(row.F3, 0.01)}</td>
                <td className="px-2 py-1.5">{scale(row.T1, 0.1)}</td>
                <td className="px-2 py-1.5">{scale(row.T3, 0.1)}</td>
                <td className="px-2 py-1.5">{row.P1 ?? '—'}</td>
                <td className="px-2 py-1.5">{row.P2 ?? '—'}</td>
                <td className="px-2 py-1.5">{row.P3 ?? '—'}</td>
                <td className="px-2 py-1.5">{row.P4 ?? '—'}</td>
                <td className="px-2 py-1.5">{row.P5 ?? '—'}</td>
                <td className="px-2 py-1.5">{theoFlow.toFixed(2)}</td>
                <td className="px-2 py-1.5">{eff.toFixed(2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
