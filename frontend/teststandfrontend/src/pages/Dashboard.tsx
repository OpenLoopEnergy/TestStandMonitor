import { useState, useEffect, useCallback } from 'react'
import { useLiveData } from '../hooks/useLiveData'
import { SignalCard } from '../components/SignalCard'
import { LiveChart } from '../components/LiveChart'
import { DataTable } from '../components/DataTable'
import { HeaderInfoPanel } from '../components/HeaderInfoPanel'
import type { ChartSignal, LogRow, SignalPoint } from '../types/signals'

const COMPUTED_SIGNALS: ChartSignal[] = ['TheoFlow', 'Efficiency']

export default function Dashboard() {
  const { data, connected } = useLiveData()
  const [inputFactor, setInputFactor] = useState(1.0)
  const [activeSignal, setActiveSignal] = useState<ChartSignal>('S1')
  const [historyPoints, setHistoryPoints] = useState<SignalPoint[]>([])
  const [theoFlowHistory, setTheoFlowHistory] = useState<SignalPoint[]>([])
  const [efficiencyHistory, setEfficiencyHistory] = useState<SignalPoint[]>([])
  const [logRows, setLogRows] = useState<LogRow[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const f1 = data.f1 * 0.01
  const theoFlow = inputFactor > 0 ? (data.s1 * inputFactor) / 231 : 0
  const efficiency = theoFlow > 0 ? (f1 / theoFlow) * 100 : 0
  const tp_pct = `${Math.floor(data.tp / 10.23)}%`

  useEffect(() => {
    const now = new Date().toISOString()
    const max = 100
    setTheoFlowHistory(prev => { const n = [...prev, { timestamp: now, value: theoFlow }]; return n.length > max ? n.slice(-max) : n })
    setEfficiencyHistory(prev => { const n = [...prev, { timestamp: now, value: efficiency }]; return n.length > max ? n.slice(-max) : n })
  }, [data])

  useEffect(() => {
    if (COMPUTED_SIGNALS.includes(activeSignal)) return
    fetch(`/get_signal_data?signal=${activeSignal}`)
      .then(r => r.json())
      .then((pts: SignalPoint[]) => setHistoryPoints(pts.reverse()))
      .catch(() => {})
  }, [activeSignal])

  useEffect(() => {
    function fetchLog() {
      fetch('/get_csv_data')
        .then(r => r.json())
        .then((res: { data: LogRow[] }) => setLogRows(res.data ?? []))
        .catch(() => {})
    }
    fetchLog()
    const id = setInterval(fetchLog, 5000)
    return () => clearInterval(id)
  }, [])

  const showToast = useCallback((type: 'success' | 'error', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3500)
  }, [])

  async function handleExport() {
    try {
      const res = await fetch('/export_data', { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? 'Export failed')
      }
      const cd = res.headers.get('Content-Disposition')
      const match = cd?.match(/filename="?([^;"]+)"?/)
      const filename = match?.[1]?.trim() ?? 'TestResults.xlsx'
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
      showToast('success', 'Exported successfully.')
    } catch (e) {
      showToast('error', `Export failed: ${e}`)
    }
  }

  async function handleClear() {
    if (!confirm('Clear the data table? This cannot be undone.')) return
    try {
      await fetch('/clear_data_table', { method: 'POST' })
      setLogRows([])
      showToast('success', 'Data table cleared.')
    } catch {
      showToast('error', 'Failed to clear data table.')
    }
  }

  function signalHistory(): SignalPoint[] {
    if (activeSignal === 'TheoFlow') return theoFlowHistory
    if (activeSignal === 'Efficiency') return efficiencyHistory
    return historyPoints
  }

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-[#1a1a1a] text-white">

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="bg-white rounded-md px-3 py-1">
            <img src="/logo.png" alt="Open Loop Energy" className="h-10 object-contain" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white/90">Test Stand Monitor</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            connected ? 'bg-green-800/60 text-green-300' : 'bg-red-900/60 text-red-300'
          }`}>
            {connected ? (data.pi_connected ? '● Pi Connected' : '● Backend Connected') : '○ Disconnected'}
          </span>
          <span className="text-xs text-gray-400">
            {data.trending === 1
              ? <span className="text-yellow-400 font-semibold">● Trending</span>
              : <span className="text-gray-500">○ Idle</span>}
          </span>
        </div>
      </div>

      {/* ── Main body ── */}
      <div className="flex flex-1 min-h-0 gap-3 p-3">

        {/* ── Left panel: signals (1/4 width, full height) ── */}
        <div className="w-1/4 shrink-0 flex flex-col gap-2 min-h-0">

          {/* System state */}
          <div className="shrink-0">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-1.5">System State</p>
            <div className="grid grid-cols-2 gap-1.5">
              <SignalCard label="SP"       value={`${data.sp} RPM`} />
              <SignalCard label="TP"       value={tp_pct} />
              <SignalCard label="Cycle"    value={`${data.cycle}`} />
              <SignalCard label="LC Set"   value={`${data.lcSetpoint} PSI`} />
              <SignalCard label="LC Reg"   value={data.lcRegulate ? 'ON' : 'OFF'} />
              <SignalCard label="Trending" value={data.trending ? 'YES' : 'NO'} />
            </div>
            <div className="mt-1.5 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
              <span className="text-xs text-gray-400">Step: </span>
              <span className="text-xs text-white/80">{data.step || '—'}</span>
            </div>
          </div>

          {/* Sensors — fills remaining height, rows distributed evenly */}
          <div className="flex-1 flex flex-col min-h-0 gap-1">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest shrink-0">Sensors</p>
            <div className="flex-1 grid grid-cols-2 gap-1.5 [grid-auto-rows:1fr]">
              {([
                ['S1',         `${data.s1} RPM`],
                ['T1',         `${(data.t1 * 0.1).toFixed(1)} °F`],
                ['T3',         `${(data.t3 * 0.1).toFixed(1)} °F`],
                ['F1',         `${f1.toFixed(2)} GPM`],
                ['F2',         `${(data.f2 * 0.01).toFixed(2)} GPM`],
                ['F3',         `${(data.f3 * 0.01).toFixed(2)} GPM`],
                ['P1',         `${data.p1} PSI`],
                ['P2',         `${data.p2} PSI`],
                ['P3',         `${data.p3} PSI`],
                ['P4',         `${data.p4} PSI`],
                ['P5',         `${data.p5} PSI`],
                ['TheoFlow',   `${theoFlow.toFixed(2)} GPM`],
                ['Efficiency', `${efficiency.toFixed(2)} %`],
              ] as [ChartSignal, string][]).map(([sig, val], i, arr) => (
                <SignalCard
                  key={sig}
                  label={sig}
                  value={val}
                  signal={sig}
                  active={activeSignal === sig}
                  onClick={setActiveSignal}
                  className={i === arr.length - 1 && arr.length % 2 !== 0 ? 'col-span-2' : ''}
                />
              ))}
            </div>
          </div>
        </div>

        {/* ── Right panel: chart + header + table (3/4 width) ── */}
        <div className="flex-1 flex flex-col gap-2 min-w-0">
          {/* Chart */}
          <div className="flex-1 bg-white/5 border border-white/10 rounded-xl p-3 flex flex-col min-h-0">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2 shrink-0">
              Chart — <span className="text-white font-semibold">{activeSignal}</span>
            </p>
            <div className="flex-1 min-h-0">
              <LiveChart signal={activeSignal} liveData={data} historyPoints={signalHistory()} />
            </div>
          </div>

          {/* Test Info */}
          <div className="shrink-0">
            <HeaderInfoPanel onInputFactorChange={setInputFactor} />
          </div>

          {/* Data Table */}
          <div className="shrink-0 bg-white/5 border border-white/10 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="font-semibold text-xs">Data Table</h2>
                <p className="text-[10px] text-gray-500">Populates when Trending · last 20 rows</p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleExport}
                  className="text-xs bg-red-700 hover:bg-red-600 px-3 py-1 rounded-lg font-medium transition-colors">
                  Export Data
                </button>
                <button onClick={handleClear}
                  className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded-lg font-medium transition-colors">
                  Clear Table
                </button>
              </div>
            </div>
            <div className="overflow-y-auto max-h-52">
              <DataTable rows={logRows} inputFactor={inputFactor} />
            </div>
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 text-sm px-4 py-3 rounded-xl shadow-lg ${
          toast.type === 'success' ? 'bg-green-800 text-green-100' : 'bg-red-800 text-red-100'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
