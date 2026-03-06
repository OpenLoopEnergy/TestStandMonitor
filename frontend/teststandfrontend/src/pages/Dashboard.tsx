import { useState, useEffect, useRef, useCallback } from 'react'
import { useLiveData } from '../hooks/useLiveData'
import { SignalCard } from '../components/SignalCard'
import { LiveChart } from '../components/LiveChart'
import { DataTable } from '../components/DataTable'
import { HeaderInfoPanel } from '../components/HeaderInfoPanel'
import type { ChartSignal, LiveData, LogRow, SignalPoint } from '../types/signals'

const COMPUTED_SIGNALS: ChartSignal[] = ['TheoFlow', 'Efficiency']
const AUTO_CLEAR_SECONDS = 15

function getLiveValue(signal: ChartSignal, d: LiveData): number | null {
  switch (signal) {
    case 'S1': return d.s1
    case 'SP': return d.sp
    case 'TP': return d.tp / 10.23
    case 'F1': return d.f1 * 0.01
    case 'F2': return d.f2 * 0.01
    case 'F3': return d.f3 * 0.01
    case 'T1': return d.t1 * 0.1
    case 'T3': return d.t3 * 0.1
    case 'P1': return d.p1
    case 'P2': return d.p2
    case 'P3': return d.p3
    case 'P4': return d.p4
    case 'P5': return d.p5
    default: return null
  }
}

export default function Dashboard() {
  const { data, connected } = useLiveData()
  const [inputFactor, setInputFactor] = useState(1.0)
  const [activeSignal, setActiveSignal] = useState<ChartSignal>('S1')
  const [historyPoints, setHistoryPoints] = useState<SignalPoint[]>([])
  const [theoFlowHistory, setTheoFlowHistory] = useState<SignalPoint[]>([])
  const [efficiencyHistory, setEfficiencyHistory] = useState<SignalPoint[]>([])
  const [logRows, setLogRows] = useState<LogRow[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [showClearModal, setShowClearModal] = useState(false)
  const [countdown, setCountdown] = useState(AUTO_CLEAR_SECONDS)
  const prevPb4 = useRef<number>(1)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const ADMIN_SESSION_KEY = 'teststand_admin'
  const LOGO_CLICK_WINDOW_MS = 5000
  const LOGO_CLICK_REQUIRED = 10
  const [isAdmin, setIsAdmin] = useState<boolean>(
    () => sessionStorage.getItem(ADMIN_SESSION_KEY) === 'true'
  )
  const [logoBounce, setLogoBounce] = useState(false)
  const logoClickTimes = useRef<number[]>([])

  const isAutomatic = data.pb4 === 0


  const f1 = data.f1 * 0.01
  const theoFlow = inputFactor > 0 ? (data.s1 * inputFactor) / 231 : 0
  const efficiency = theoFlow > 0 ? (f1 / theoFlow) * 100 : 0
  const tp_pct = `${Math.floor(data.tp / 10.23)}%`

  const showToast = useCallback((type: 'success' | 'error', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3500)
  }, [])

  function handleLogoClick() {
    const now = Date.now()
    const recent = [...logoClickTimes.current, now].filter(t => now - t < LOGO_CLICK_WINDOW_MS)
    logoClickTimes.current = recent
    if (recent.length >= LOGO_CLICK_REQUIRED) {
      logoClickTimes.current = []
      const next = !isAdmin
      sessionStorage.setItem(ADMIN_SESSION_KEY, String(next))
      setIsAdmin(next)
      if (next) setLogoBounce(true)
    }
  }

  useEffect(() => {
    if (!logoBounce) return
    const id = setTimeout(() => setLogoBounce(false), 600)
    return () => clearTimeout(id)
  }, [logoBounce])

  async function handleDebugToggle() {
    await fetch('/set_debug_mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !data.debug_mode }),
    })
  }

  async function doClear() {
    try {
      await fetch('/clear_data_table', { method: 'POST' })
      setLogRows([])
      showToast('success', 'Data table cleared.')
    } catch {
      showToast('error', 'Failed to clear data table.')
    }
  }

  // Detect Manual → Automatic transition and show the clear prompt
  // Only trigger once Pi is connected to avoid false positives on page load
  useEffect(() => {
    if (data.pi_connected && data.pb4 === 0 && prevPb4.current === 1) {
      if (isAdmin) {
        setCountdown(AUTO_CLEAR_SECONDS)
        setShowClearModal(true)
      }
    }
    prevPb4.current = data.pb4
  }, [data.pb4, isAdmin])

  // Countdown timer when modal is visible
  useEffect(() => {
    if (!showClearModal) {
      if (countdownRef.current) clearInterval(countdownRef.current)
      return
    }
    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownRef.current!)
          setShowClearModal(false)
          doClear()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => { if (countdownRef.current) clearInterval(countdownRef.current) }
  }, [showClearModal])

  useEffect(() => {
    const now = new Date().toISOString()
    const max = 100
    setTheoFlowHistory(prev => { const n = [...prev, { timestamp: now, value: theoFlow }]; return n.length > max ? n.slice(-max) : n })
    setEfficiencyHistory(prev => { const n = [...prev, { timestamp: now, value: efficiency }]; return n.length > max ? n.slice(-max) : n })
  }, [data])

  // Clear history when switching to a non-computed signal
  useEffect(() => {
    if (!COMPUTED_SIGNALS.includes(activeSignal)) setHistoryPoints([])
  }, [activeSignal])

  // Accumulate live data for non-computed signals (up to 100 points)
  useEffect(() => {
    if (COMPUTED_SIGNALS.includes(activeSignal)) return
    const val = getLiveValue(activeSignal, data)
    if (val === null) return
    const now = new Date().toISOString()
    setHistoryPoints(prev => {
      const n = [...prev, { timestamp: now, value: val }]
      return n.length > 100 ? n.slice(-100) : n
    })
  }, [data])

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
    await doClear()
  }

  function signalHistory(): SignalPoint[] {
    if (activeSignal === 'TheoFlow') return theoFlowHistory
    if (activeSignal === 'Efficiency') return efficiencyHistory
    return historyPoints
  }

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-[#1a1a1a] text-white">

      {/* ── Auto-clear Modal ── */}
      {isAdmin && showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-[#232323] border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
            <div className={`text-center mb-1 text-xs font-bold uppercase tracking-widest ${isAutomatic ? 'text-blue-400' : 'text-gray-400'}`}>
              Automatic Mode Detected
            </div>
            <h2 className="text-xl font-bold text-center mb-2">Clear Data Table?</h2>
            <p className="text-sm text-gray-400 text-center mb-6">
              It looks like you're starting an automatic test. The data table should be cleared before each test to avoid mixing results.
              Auto-clearing in <span className="text-white font-bold text-lg">{countdown}</span>s…
            </p>
            <div className="w-full bg-white/10 rounded-full h-1.5 mb-6">
              <div
                className="bg-red-600 h-1.5 rounded-full transition-all duration-1000"
                style={{ width: `${(countdown / AUTO_CLEAR_SECONDS) * 100}%` }}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowClearModal(false); doClear() }}
                className="flex-1 bg-red-700 hover:bg-red-600 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Clear Data Table Now
              </button>
              <button
                onClick={() => setShowClearModal(false)}
                className="flex-1 bg-white/10 hover:bg-white/20 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Keep Data
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-4">
          <div
            className={`bg-white rounded-md px-3 py-1 cursor-pointer select-none outline-none${logoBounce ? ' logo-bounce' : ''}`}
            style={{ WebkitTapHighlightColor: 'transparent' }}
            onClick={handleLogoClick}
            title={isAdmin ? 'Admin mode active — click 10× to deactivate' : ''}
          >
            <img src="/logo.png" alt="Open Loop Energy" className="h-10 object-contain pointer-events-none" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white/90">Test Stand Monitor</span>
        </div>
        <div className="flex items-center gap-3">
          {isAdmin && (
            <span className="text-xs px-2 py-1 rounded-full font-bold bg-amber-900/60 text-amber-300 border border-amber-700/50">
              Admin
            </span>
          )}
          {isAdmin && (
            <button
              onClick={handleDebugToggle}
              className={`text-xs px-2 py-1 rounded-full font-bold border transition-colors ${
                data.debug_mode
                  ? 'bg-orange-900/60 text-orange-300 border-orange-700/50'
                  : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10'
              }`}
            >
              {data.debug_mode ? '● Debug' : '○ Debug'}
            </button>
          )}
          {/* Mode — prominent */}
          <span className={`text-sm px-3 py-1 rounded-full font-bold border ${
            isAutomatic
              ? 'bg-blue-900/60 text-blue-300 border-blue-700'
              : 'bg-white/5 text-gray-300 border-white/10'
          }`}>
            {isAutomatic ? '⚙ Automatic' : '✋ Manual'}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            connected ? 'bg-green-800/60 text-green-300' : 'bg-red-900/60 text-red-300'
          }`}>
            {connected ? '● Backend' : '○ Backend'}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            data.pi_connected ? 'bg-green-800/60 text-green-300' : 'bg-red-900/60 text-red-300'
          }`}>
            {data.pi_connected ? '● Raspberry Pi' : '○ Raspberry Pi'}
          </span>
          <span className="text-xs text-gray-400">
            {data.trending === 1
              ? <span className="text-yellow-400 font-semibold">● Trending</span>
              : <span className="text-gray-500">○ Idle</span>}
          </span>
          <a
            href="/past-tests"
            className="text-sm bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg font-semibold transition-colors"
          >
            Past Tests
          </a>
        </div>
      </div>

      {/* ── Main body ── */}
      <div className="flex flex-1 min-h-0 gap-3 p-3">

        {/* ── Left panel: signals (1/4 width, full height) ── */}
        <div className="w-1/4 shrink-0 flex flex-col gap-2 min-h-0">

          {/* System state */}
          <div className="shrink-0">
            <p className="text-xs text-white/50 uppercase tracking-widest mb-1.5">System State</p>
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
            <p className="text-xs text-white/50 uppercase tracking-widest shrink-0">Sensors</p>
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
            <p className="text-xs text-white/50 uppercase tracking-widest mb-2 shrink-0">
              Chart — <span className="text-white font-semibold">{activeSignal}</span>
            </p>
            <div className="flex-1 min-h-0">
              <LiveChart signal={activeSignal} liveData={data} historyPoints={signalHistory()} />
            </div>
          </div>

          {/* Test Info */}
          <div className="shrink-0">
            <HeaderInfoPanel onInputFactorChange={setInputFactor} isAdmin={isAdmin} />
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
                {isAdmin && (
                  <button onClick={handleClear}
                    className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded-lg font-medium transition-colors">
                    Clear Table
                  </button>
                )}
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
