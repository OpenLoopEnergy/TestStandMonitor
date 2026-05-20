import { useState, useEffect, useRef, useCallback } from 'react'
import { useLiveData } from '../hooks/useLiveData'
import { SignalCard } from '../components/SignalCard'
import { LiveChart } from '../components/LiveChart'
import { DataTable } from '../components/DataTable'
import { HeaderInfoPanel } from '../components/HeaderInfoPanel'
import { ThemeToggle } from '../components/ThemeToggle'
import type { ChartSignal, LiveData, LogRow, SignalPoint } from '../types/signals'

const COMPUTED_SIGNALS: ChartSignal[] = ['TheoFlow', 'EfficiencyA', 'EfficiencyB']
const EFFICIENCY_SIGNALS = new Set<ChartSignal>(['EfficiencyA', 'EfficiencyB'])

function signalDisplayName(s: ChartSignal): string {
  if (s === 'EfficiencyA') return 'Efficiency A'
  if (s === 'EfficiencyB') return 'Efficiency B'
  return s
}
const AUTO_CLEAR_SECONDS = 15

function getLiveValue(signal: ChartSignal, d: LiveData): number | null {
  switch (signal) {
    case 'S1': return d.s1
    case 'SP': return d.sp
    case 'TP': return d.tp / 10.23
    case 'F1': return d.f1 * 0.01
    case 'F2': return d.f2 * 0.001
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
  const { data, connected, piConnected } = useLiveData()
  const [inputFactor, setInputFactor] = useState(1.0)
  const [activeSignals, setActiveSignals] = useState<ChartSignal[]>(['S1'])
  const [historyPoints, setHistoryPoints] = useState<SignalPoint[]>([])
  const [theoFlowHistory, setTheoFlowHistory] = useState<SignalPoint[]>([])
  const [efficiencyAHistory, setEfficiencyAHistory] = useState<SignalPoint[]>([])
  const [efficiencyBHistory, setEfficiencyBHistory] = useState<SignalPoint[]>([])
  const [logRows, setLogRows] = useState<LogRow[]>([])
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [showClearModal, setShowClearModal] = useState(false)
  const [showLogManualModal, setShowLogManualModal] = useState(false)
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
  const primarySignal = activeSignals[0]

  function handleSignalClick(signal: ChartSignal) {
    if (!EFFICIENCY_SIGNALS.has(signal)) {
      setActiveSignals([signal])
      return
    }
    // In efficiency mode already: toggle this signal in/out
    if (activeSignals.every(s => EFFICIENCY_SIGNALS.has(s))) {
      if (activeSignals.includes(signal)) {
        // Don't allow deselecting the last one
        const remaining = activeSignals.filter(s => s !== signal)
        if (remaining.length > 0) setActiveSignals(remaining)
      } else {
        // Add and keep alphabetical order (A before B)
        setActiveSignals([...activeSignals, signal].sort() as ChartSignal[])
      }
    } else {
      // Coming from a non-efficiency selection — start fresh
      setActiveSignals([signal])
    }
  }

  const f1 = data.f1 * 0.01
  const f3 = data.f3 * 0.01
  const theoFlow = inputFactor > 0 ? (data.s1 * inputFactor) / 231 : 0
  const efficiencyA = theoFlow > 0 ? (f3 / theoFlow) * 100 : 0  // A = F3 forward
  const efficiencyB = theoFlow > 0 ? (f1 / theoFlow) * 100 : 0  // B = F1 reverse
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

  async function handleLogManualToggle() {
    if (!data.log_manual) {
      setShowLogManualModal(true)
    } else {
      await fetch('/set_log_manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: false }),
      })
    }
  }

  async function handleLogManualConfirm() {
    setShowLogManualModal(false)
    await fetch('/set_log_manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: true }),
    })
  }

  const doClear = useCallback(async () => {
    try {
      await fetch('/clear_data_table', { method: 'POST' })
      setLogRows([])
      showToast('success', 'Data table cleared.')
    } catch {
      showToast('error', 'Failed to clear data table.')
    }
  }, [showToast])

  // Detect Manual → Automatic transition and show the clear prompt
  // Only trigger once Pi is connected to avoid false positives on page load
  useEffect(() => {
    if (piConnected && data.pb4 === 0 && prevPb4.current === 1) {
      if (isAdmin) {
        setCountdown(AUTO_CLEAR_SECONDS)
        setShowClearModal(true)
      }
    }
    prevPb4.current = data.pb4
  }, [data.pb4, piConnected, isAdmin])

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
  }, [showClearModal, doClear])

  useEffect(() => {
    const now = new Date().toISOString()
    const max = 100
    setTheoFlowHistory(prev =>  { const n = [...prev, { timestamp: now, value: theoFlow   }]; return n.length > max ? n.slice(-max) : n })
    setEfficiencyAHistory(prev => { const n = [...prev, { timestamp: now, value: efficiencyA }]; return n.length > max ? n.slice(-max) : n })
    setEfficiencyBHistory(prev => { const n = [...prev, { timestamp: now, value: efficiencyB }]; return n.length > max ? n.slice(-max) : n })
  }, [data, efficiencyA, efficiencyB, theoFlow])

  // Clear accumulated history when switching to a new non-computed signal
  useEffect(() => {
    if (!COMPUTED_SIGNALS.includes(primarySignal)) setHistoryPoints([])
  }, [primarySignal])

  // Accumulate live data for non-computed signals (up to 100 points)
  useEffect(() => {
    if (COMPUTED_SIGNALS.includes(primarySignal)) return
    const val = getLiveValue(primarySignal, data)
    if (val === null) return
    const now = new Date().toISOString()
    setHistoryPoints(prev => {
      const n = [...prev, { timestamp: now, value: val }]
      return n.length > 100 ? n.slice(-100) : n
    })
  }, [data, primarySignal])

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
    setIsExporting(true)
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
    } finally {
      setIsExporting(false)
    }
  }

  async function handleClear() {
    if (!confirm('Clear the data table? This cannot be undone.')) return
    await doClear()
  }

  function signalHistory(): SignalPoint[] {
    if (primarySignal === 'TheoFlow') return theoFlowHistory
    if (primarySignal === 'EfficiencyA') return efficiencyAHistory
    if (primarySignal === 'EfficiencyB') return efficiencyBHistory
    return historyPoints
  }

  function signalHistoryB(): SignalPoint[] | undefined {
    // Only supplied when both efficiency signals are active (signals[1] is always EfficiencyB)
    return activeSignals.length === 2 ? efficiencyBHistory : undefined
  }

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-gray-100 text-gray-900 dark:bg-[#1a1a1a] dark:text-white">

      {/* ── Export Loading Overlay ── */}
      {isExporting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-white border border-gray-200 rounded-2xl px-10 py-8 flex flex-col items-center gap-4 shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <div className="w-10 h-10 border-4 border-black/20 border-t-red-500 rounded-full animate-spin dark:border-white/20" />
            <p className="text-gray-900 font-semibold text-base dark:text-white">Building Export…</p>
            <p className="text-gray-600 text-sm dark:text-gray-400">Generating Excel file, this may take a moment.</p>
          </div>
        </div>
      )}

      {/* ── Auto-clear Modal ── */}
      {isAdmin && showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <div className={`text-center mb-1 text-xs font-bold uppercase tracking-widest ${isAutomatic ? 'text-blue-500 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`}>
              Automatic Mode Detected
            </div>
            <h2 className="text-xl font-bold text-center mb-2 text-gray-900 dark:text-white">Clear Data Table?</h2>
            <p className="text-sm text-gray-600 text-center mb-6 dark:text-gray-400">
              It looks like you're starting an automatic test. The data table should be cleared before each test to avoid mixing results.
              Auto-clearing in <span className="text-gray-900 font-bold text-lg dark:text-white">{countdown}</span>s…
            </p>
            <div className="w-full bg-black/10 rounded-full h-1.5 mb-6 dark:bg-white/10">
              <div
                className="bg-red-600 h-1.5 rounded-full transition-all duration-1000"
                style={{ width: `${(countdown / AUTO_CLEAR_SECONDS) * 100}%` }}
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowClearModal(false); doClear() }}
                className="flex-1 bg-red-700 hover:bg-red-600 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Clear Data Table Now
              </button>
              <button
                onClick={() => setShowClearModal(false)}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-900 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
              >
                Keep Data
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Log Manual Confirmation Modal ── */}
      {isAdmin && showLogManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <div className="text-center mb-1 text-xs font-bold uppercase tracking-widest text-teal-600 dark:text-teal-400">
              Log Manual Mode
            </div>
            <h2 className="text-xl font-bold text-center mb-2 text-gray-900 dark:text-white">Enable Manual Logging?</h2>
            <p className="text-sm text-gray-600 text-center mb-6 dark:text-gray-400">
              Rows will be logged every{' '}
              <span className="font-bold text-gray-900 dark:text-white">
                {data.debug_mode ? '0.5s' : '5s'}
              </span>{' '}
              while the machine is in Manual mode. This can fill the table quickly.
              Clear the table before starting a test to keep results clean.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleLogManualConfirm}
                className="flex-1 bg-teal-700 hover:bg-teal-600 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Enable Log Manual
              </button>
              <button
                onClick={() => setShowLogManualModal(false)}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-900 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/10 shrink-0 dark:border-white/10">
        <div className="flex items-center gap-4">
          <div
            className={`bg-white border border-gray-200 rounded-md px-4 py-2 cursor-pointer select-none outline-none dark:border-transparent${logoBounce ? ' logo-bounce' : ''}`}
            style={{ WebkitTapHighlightColor: 'transparent' }}
            onClick={handleLogoClick}
            title={isAdmin ? 'Admin mode active — click 10× to deactivate' : ''}
          >
            <img src="/logo.png" alt="Open Loop Energy" className="h-14 object-contain pointer-events-none" />
          </div>
          <span className="text-lg font-bold tracking-tight text-gray-900 dark:text-white/90">Test Stand Monitor</span>
        </div>
        <div className="flex items-center gap-3">
          {isAdmin && (
            <span className="text-xs px-2 py-1 rounded-full font-bold bg-amber-100 text-amber-700 border border-amber-300 dark:bg-amber-900/60 dark:text-amber-300 dark:border-amber-700/50">
              Admin
            </span>
          )}
          {isAdmin && (
            <button
              onClick={handleDebugToggle}
              className={`cursor-pointer text-sm px-4 py-2 rounded-full font-bold border transition-colors ${
                data.debug_mode
                  ? 'bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/60 dark:text-orange-300 dark:border-orange-700/50'
                  : 'bg-black/5 text-gray-600 border-black/10 hover:bg-black/10 dark:bg-white/5 dark:text-gray-400 dark:border-white/10 dark:hover:bg-white/10'
              }`}
            >
              {data.debug_mode ? '● Debug' : '○ Debug'}
            </button>
          )}
          {isAdmin && (
            <button
              onClick={handleLogManualToggle}
              className={`cursor-pointer text-sm px-4 py-2 rounded-full font-bold border transition-colors ${
                data.log_manual
                  ? 'bg-teal-100 text-teal-700 border-teal-300 dark:bg-teal-900/60 dark:text-teal-300 dark:border-teal-700/50'
                  : 'bg-black/5 text-gray-600 border-black/10 hover:bg-black/10 dark:bg-white/5 dark:text-gray-400 dark:border-white/10 dark:hover:bg-white/10'
              }`}
            >
              {data.log_manual ? '● Log Manual' : '○ Log Manual'}
            </button>
          )}
          {/* Mode — prominent */}
          <span className={`text-sm px-3 py-1 rounded-full font-bold border ${
            isAutomatic
              ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/60 dark:text-blue-300 dark:border-blue-700'
              : 'bg-black/5 text-gray-600 border-black/10 dark:bg-white/5 dark:text-gray-300 dark:border-white/10'
          }`}>
            {isAutomatic ? '⚙ Automatic' : '✋ Manual'}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            connected ? 'bg-green-100 text-green-700 dark:bg-green-800/60 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300'
          }`}>
            {connected ? '● Backend' : '○ Backend'}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
            piConnected ? 'bg-green-100 text-green-700 dark:bg-green-800/60 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300'
          }`}>
            {piConnected ? '● Raspberry Pi' : '○ Raspberry Pi'}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {data.trending === 1
              ? <span className="text-yellow-600 font-semibold dark:text-yellow-400">● Trending</span>
              : <span className="text-gray-400 dark:text-gray-500">○ Idle</span>}
          </span>
          <ThemeToggle />
          {isAdmin && (
            <a
              href="/debug"
              className="cursor-pointer text-sm bg-black/10 hover:bg-black/20 text-gray-900 px-4 py-2 rounded-lg font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
            >
              Debug
            </a>
          )}
          <a
            href="/past-tests"
            className="cursor-pointer text-base bg-black/10 hover:bg-black/20 text-gray-900 px-5 py-2.5 rounded-lg font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
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
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-1.5 dark:text-white/50">System State</p>
            <div className="grid grid-cols-2 gap-1.5">
              <SignalCard label="SP"       value={`${data.sp} RPM`} />
              <SignalCard label="TP"       value={tp_pct} />
              <SignalCard label="Cycle"    value={`${data.cycle}`} />
              <SignalCard label="LC Set"   value={`${data.lcSetpoint} PSI`} />
              <SignalCard label="LC Reg"   value={data.lcRegulate ? 'ON' : 'OFF'} />
              <SignalCard label="Trending" value={data.trending ? 'YES' : 'NO'} />
            </div>
            <div className="mt-1.5 bg-black/5 border border-black/10 rounded-lg px-3 py-1.5 dark:bg-white/5 dark:border-white/10">
              <span className="text-xs text-gray-600 dark:text-gray-400">Step: </span>
              <span className="text-xs text-gray-700 dark:text-white/80">{data.step || '—'}</span>
            </div>
          </div>

          {/* Sensors — fills remaining height, rows distributed evenly */}
          <div className="flex-1 flex flex-col min-h-0 gap-1">
            <p className="text-xs text-gray-500 uppercase tracking-widest shrink-0 dark:text-white/50">Sensors</p>
            <div className="flex-1 grid grid-cols-2 gap-1.5 [grid-auto-rows:1fr]">
              {([
                ['S1',         `${data.s1} RPM`],
                ['T1',         `${(data.t1 * 0.1).toFixed(1)} °F`],
                ['T3',         `${(data.t3 * 0.1).toFixed(1)} °F`],
                ['F1',         `${f1.toFixed(2)} GPM`],
                ['F2',         `${(data.f2 * 0.001).toFixed(3)} GPM`],
                ['F3',         `${(data.f3 * 0.01).toFixed(2)} GPM`],
                ['P1',         `${data.p1} PSI`],
                ['P2',         `${data.p2} PSI`],
                ['P3',         `${data.p3} PSI`],
                ['P4',         `${data.p4} PSI`],
                ['P5',         `${data.p5} PSI`],
                ['TheoFlow',   `${theoFlow.toFixed(2)} GPM`],
                ['EfficiencyA', `${efficiencyA.toFixed(2)} %`],
                ['EfficiencyB', `${efficiencyB.toFixed(2)} %`],
              ] as [ChartSignal, string][]).map(([sig, val], i, arr) => (
                <SignalCard
                  key={sig}
                  label={signalDisplayName(sig)}
                  value={val}
                  signal={sig}
                  active={activeSignals.includes(sig)}
                  onClick={handleSignalClick}
                  className={i === arr.length - 1 && arr.length % 2 !== 0 ? 'col-span-2' : ''}
                />
              ))}
            </div>
          </div>
        </div>

        {/* ── Right panel: chart + header + table (3/4 width) ── */}
        <div className="flex-1 flex flex-col gap-2 min-w-0">
          {/* Chart */}
          <div className="flex-1 bg-black/5 border border-black/10 rounded-xl p-3 flex flex-col min-h-0 dark:bg-white/5 dark:border-white/10">
            <p className="text-xs text-gray-500 uppercase tracking-widest mb-2 shrink-0 dark:text-white/50">
              Chart — <span className="text-gray-900 font-semibold dark:text-white">{activeSignals.map(signalDisplayName).join(' · ')}</span>
            </p>
            <div className="flex-1 min-h-0">
              <LiveChart signals={activeSignals} historyPoints={signalHistory()} historyPointsB={signalHistoryB()} />
            </div>
          </div>

          {/* Test Info */}
          <div className="shrink-0">
            <HeaderInfoPanel onInputFactorChange={setInputFactor} isAdmin={isAdmin} />
          </div>

          {/* Data Table */}
          <div className="shrink-0 bg-black/5 border border-black/10 rounded-xl p-3 dark:bg-white/5 dark:border-white/10">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="font-semibold text-xs">Data Table</h2>
                <p className="text-[10px] text-gray-500">
                  {data.log_manual
                    ? 'Populates when Trending or in Manual mode · last 20 rows'
                    : 'Populates when Trending · last 20 rows'}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleExport} disabled={isExporting}
                  className="cursor-pointer text-sm bg-red-700 hover:bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed px-5 py-2.5 rounded-lg font-semibold transition-colors">
                  {isExporting ? 'Exporting…' : 'Export Data'}
                </button>
                {isAdmin && (
                  <button onClick={handleClear}
                    className="cursor-pointer text-sm bg-black/10 hover:bg-black/20 text-gray-900 px-5 py-2.5 rounded-lg font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white">
                    Clear Table
                  </button>
                )}
              </div>
            </div>
            <div className="overflow-y-auto max-h-52">
              <DataTable rows={logRows} inputFactor={inputFactor} logManual={data.log_manual} />
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
