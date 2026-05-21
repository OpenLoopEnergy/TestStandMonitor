import { useState, useEffect } from 'react'
import { useLiveData } from '../hooks/useLiveData'
import { ThemeToggle } from '../components/ThemeToggle'
import { LiveChart } from '../components/LiveChart'
import type { M1PortsData, M2PortsData, SignalPoint } from '../types/signals'

const HISTORY_MAX    = 100
const ADMIN_KEY      = 'teststand_admin'

// ── Badges ────────────────────────────────────────────────────────────────────

function FaultBadge({ value }: { value: number | undefined }) {
  if (value === undefined)
    return <span className="text-gray-400 dark:text-gray-600">—</span>
  if (value === 0)
    return <span className="inline-block px-2 py-px rounded text-[12px] font-bold bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300">OK</span>
  return <span className="inline-block px-2 py-px rounded text-[12px] font-bold bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300">Fault</span>
}

function ActiveBadge({ value, onLabel = 'Yes', offLabel = 'No' }: {
  value: number | undefined; onLabel?: string; offLabel?: string
}) {
  if (value === undefined)
    return <span className="text-gray-400 dark:text-gray-600">—</span>
  if (value === 1)
    return <span className="inline-block px-2 py-px rounded text-[12px] font-bold bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300">{onLabel}</span>
  return <span className="inline-block px-2 py-px rounded text-[12px] font-bold bg-black/5 text-gray-500 dark:bg-white/5 dark:text-gray-400">{offLabel}</span>
}

// ── Port table data ────────────────────────────────────────────────────────────

const M1_CIRCUITS: { label: string; open: keyof M1PortsData; short: keyof M1PortsData }[] = [
  { label: 'SP',        open: 'sp_open',        short: 'sp_short' },
  { label: 'SP Enable', open: 'sp_enable_open', short: 'sp_enable_short' },
  { label: 'SP Rev',    open: 'sp_rev_open',    short: 'sp_rev_short' },
  { label: 'TP',        open: 'tp_open',        short: 'tp_short' },
  { label: 'TP Enable', open: 'tp_enable_open', short: 'tp_enable_short' },
  { label: 'TP Rev',    open: 'tp_rev_open',    short: 'tp_rev_short' },
  { label: 'LC1',       open: 'lc1_open',       short: 'lc1_short' },
  { label: 'LC1 PWR',   open: 'lc1_pwr_open',  short: 'lc1_pwr_short' },
  { label: 'LED',       open: 'led_open',       short: 'led_short' },
]

const M2_CIRCUITS: { label: string; open: keyof M2PortsData; short: keyof M2PortsData }[] = [
  { label: 'Polarity',  open: 'polarity_open',  short: 'polarity_short' },
  { label: 'Stop Lamp', open: 'stop_lamp_open', short: 'stop_lamp_short' },
  { label: 'Sol A',     open: 'sol_a_open',     short: 'sol_a_short' },
  { label: 'Sol B',     open: 'sol_b_open',     short: 'sol_b_short' },
  { label: 'TP9A',      open: 'tp9a_open',      short: 'tp9a_short' },
  { label: 'TP9A FWD',  open: 'tp9a_fwd_open',  short: 'tp9a_fwd_short' },
  { label: 'TP9A REV',  open: 'tp9a_rev_open',  short: 'tp9a_rev_short' },
]

const TH = 'text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 pb-2'
const TD = 'py-1 text-[13px] text-gray-700 dark:text-gray-300'
const TR = 'border-b border-black/[0.04] dark:border-white/[0.04] last:border-0'

function M1PortTable({ ports }: { ports: M1PortsData | undefined }) {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-black/10 dark:border-white/10">
          <th className={`${TH} text-left`}>Circuit</th>
          <th className={`${TH} text-center w-10`}>Open</th>
          <th className={`${TH} text-center w-10`}>Short</th>
        </tr>
      </thead>
      <tbody>
        {M1_CIRCUITS.map(({ label, open, short }) => (
          <tr key={label} className={TR}>
            <td className={TD}>{label}</td>
            <td className={`${TD} text-center`}><FaultBadge value={ports?.[open]} /></td>
            <td className={`${TD} text-center`}><FaultBadge value={ports?.[short]} /></td>
          </tr>
        ))}
        <tr className={TR}>
          <td className={TD}>M1 Blink</td>
          <td className={`${TD} text-center font-mono`} colSpan={2}>
            {ports?.m1_blink !== undefined ? ports.m1_blink : <span className="text-gray-400 dark:text-gray-600">—</span>}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

function M2PortTable({ ports }: { ports: M2PortsData | undefined }) {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-black/10 dark:border-white/10">
          <th className={`${TH} text-left`}>Circuit</th>
          <th className={`${TH} text-center w-10`}>Open</th>
          <th className={`${TH} text-center w-10`}>Short</th>
        </tr>
      </thead>
      <tbody>
        {M2_CIRCUITS.map(({ label, open, short }) => (
          <tr key={label} className={TR}>
            <td className={TD}>{label}</td>
            <td className={`${TD} text-center`}><FaultBadge value={ports?.[open] as number | undefined} /></td>
            <td className={`${TD} text-center`}><FaultBadge value={ports?.[short] as number | undefined} /></td>
          </tr>
        ))}
        <tr className={TR}>
          <td className={TD}>M2 Blink</td>
          <td className={`${TD} text-center font-mono`} colSpan={2}>
            {ports?.m2_blink !== undefined ? ports.m2_blink : <span className="text-gray-400 dark:text-gray-600">—</span>}
          </td>
        </tr>
        <tr>
          <td className={TD}>Supply Voltage</td>
          <td className={`${TD} text-center font-semibold text-gray-900 dark:text-white`} colSpan={2}>
            {ports?.supply_voltage !== undefined
              ? `${(ports.supply_voltage * 0.0339).toFixed(2)} V`
              : <span className="text-gray-400 dark:text-gray-600">—</span>}
          </td>
        </tr>
      </tbody>
    </table>
  )
}

// ── Color-coded data row ───────────────────────────────────────────────────────
// vt = value type — controls the color of the value text

type ValueType = 'psi' | 'gpm' | 'rpm' | 'temp' | 'pct' | 'raw' | undefined

const VT_COLOR: Record<NonNullable<ValueType>, string> = {
  psi:  'text-blue-400 dark:text-blue-300',
  gpm:  'text-cyan-400 dark:text-cyan-300',
  rpm:  'text-amber-400 dark:text-amber-300',
  temp: 'text-orange-400 dark:text-orange-300',
  pct:  'text-purple-400 dark:text-purple-300',
  raw:  'text-gray-400 dark:text-gray-500',
}

function D({ label, value, vt }: { label: string; value: React.ReactNode; vt?: ValueType }) {
  const valClass = vt ? VT_COLOR[vt] : 'text-gray-900 dark:text-white'
  return (
    <div className="flex items-center justify-between py-[5px] border-b border-black/[0.04] dark:border-white/[0.04]">
      <span className="text-[13px] text-gray-500 dark:text-gray-400 truncate mr-1">{label}</span>
      <span className={`text-[13px] font-semibold whitespace-nowrap shrink-0 ${valClass}`}>{value}</span>
    </div>
  )
}

function S({ title }: { title: string }) {
  return (
    <p className="col-span-2 mt-3 mb-1 text-[11px] uppercase tracking-widest text-gray-400 dark:text-gray-500 first:mt-0">{title}</p>
  )
}

const CARD       = 'flex flex-col bg-black/[0.03] border border-black/[0.08] rounded-xl p-3 dark:bg-white/[0.03] dark:border-white/[0.08]'
const CARD_TITLE = 'text-[13px] font-bold uppercase tracking-wide mb-2 shrink-0 text-gray-600 dark:text-gray-300'

// ── Main component ─────────────────────────────────────────────────────────────

export default function Debug() {
  // Admin gate — redirect to dashboard if not in admin mode
  useEffect(() => {
    if (sessionStorage.getItem(ADMIN_KEY) !== 'true') {
      window.location.replace('/')
    }
  }, [])

  const { data, connected, piConnected } = useLiveData()

  // Scale the entire page to fill whatever screen/TV is being used.
  // Design reference: 1400 × 820. On a 1080p TV this gives ~1.3x (bigger/easier
  // to read); on a small laptop it scales down so nothing is clipped.
  const [scale, setScale] = useState(1)
  useEffect(() => {
    const DESIGN_W = 1400, DESIGN_H = 820
    const update = () => {
      const s = Math.min(window.innerWidth / DESIGN_W, window.innerHeight / DESIGN_H)
      setScale(parseFloat(s.toFixed(4)))
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  const [inputFactor, setInputFactor] = useState(11)
  const [effAHistory, setEffAHistory] = useState<SignalPoint[]>([])
  const [effBHistory, setEffBHistory] = useState<SignalPoint[]>([])
  const [isExporting, setIsExporting] = useState(false)

  useEffect(() => {
    fetch('/get_header_data')
      .then(r => r.json())
      .then(d => {
        const v = parseFloat(d.inputFactor)
        if (!isNaN(v) && v > 0) setInputFactor(v)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const s1 = data.s1 ?? 0
    const f1 = (data.f1 ?? 0) * 0.01
    const f3 = (data.f3 ?? 0) * 0.01
    const theoFlow = inputFactor > 0 ? (s1 * inputFactor) / 231 : 0
    const effA = theoFlow > 0 ? (f3 / theoFlow) * 100 : 0
    const effB = theoFlow > 0 ? (f1 / theoFlow) * 100 : 0
    const ts = new Date().toISOString()
    setEffAHistory(prev => [...prev.slice(-(HISTORY_MAX - 1)), { timestamp: ts, value: effA }])
    setEffBHistory(prev => [...prev.slice(-(HISTORY_MAX - 1)), { timestamp: ts, value: effB }])
  }, [data, inputFactor])

  async function handleLogManualToggle() {
    await fetch('/set_log_manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !data.log_manual }),
    })
  }

  async function handleExport() {
    setIsExporting(true)
    try {
      const res = await fetch('/export_debug_data', { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Export failed' }))
        alert(err.detail ?? 'Export failed')
        return
      }
      const blob = await res.blob()
      const cd   = res.headers.get('content-disposition') ?? ''
      const name = cd.match(/filename="?([^"]+)"?/)?.[1] ?? 'Debug_Export.xlsx'
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = name; a.click()
      URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }

  async function handleClear() {
    if (!window.confirm('Clear all debug log data? This cannot be undone.')) return
    await fetch('/clear_debug_table', { method: 'POST' })
  }

  const isAutomatic   = data.pb4 === 0
  const f1            = (data.f1 ?? 0) * 0.01
  const f2            = (data.f2 ?? 0) * 0.001
  const f3            = (data.f3 ?? 0) * 0.01
  const t1            = ((data.t1 ?? 0) * 0.1).toFixed(1)
  const t3            = ((data.t3 ?? 0) * 0.1).toFixed(1)
  const tp_pct        = ((data.tp ?? 0) / 10.23).toFixed(1)
  const delay_s       = ((data.delay ?? 0) * 0.01).toFixed(2)
  const cycleTimer_s  = ((data.cycleTimer ?? 0) * 0.01).toFixed(2)
  const dirLabel      = data.ee_dir_switch === 0 ? 'Both' : data.ee_dir_switch === 1 ? 'Forward' : 'Backward'
  const fps           = data.pi_fps ?? 0
  const rowsLogged    = data.debug_rows_logged ?? 0

  // transform: scale keeps layout unchanged but scales visually.
  // Expanding width/height by 1/scale ensures the div fills the viewport
  // exactly once the scale is applied.
  const scaleStyle: React.CSSProperties = scale !== 1 ? {
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    width:  `${(100 / scale).toFixed(3)}vw`,
    height: `${(100 / scale).toFixed(3)}vh`,
  } : {}

  return (
    <div
      style={scaleStyle}
      className="h-screen flex flex-col bg-white text-gray-900 overflow-hidden dark:bg-[#1a1a1a] dark:text-white"
    >

      {/* ── Header ── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/10 shrink-0 dark:border-white/10">
        <div className="flex items-center gap-3">
          <div className="bg-white border border-gray-200 rounded-md px-4 py-2 dark:border-transparent">
            <img src="/logo.png" alt="Open Loop Energy" className="h-14 object-contain" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-gray-900 dark:text-white/90">Debug</span>
            <p className="text-xs text-gray-500 dark:text-gray-400">Diagnostics &amp; live signal monitor — admin only</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
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
            {piConnected ? `● Pi  ${fps} fps` : '○ Raspberry Pi'}
          </span>
          <ThemeToggle />
          <a href="/" className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1.5 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white">
            ← Dashboard
          </a>
          <a href="/past-tests" className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1.5 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white">
            Past Tests
          </a>
        </div>
      </div>

      {/* ── Body: three columns ── */}
      <div className="flex flex-1 min-h-0 gap-3 p-3 pb-0 overflow-hidden">

        {/* Col 1: Port tables + Efficiency chart */}
        <div className="flex flex-col gap-3 w-[32%] shrink-0 min-h-0">
          <div className="flex gap-3 shrink-0">
            <div className={`${CARD} flex-1`}>
              <h2 className={CARD_TITLE}>M1 Ports</h2>
              <M1PortTable ports={data.m1_ports} />
            </div>
            <div className={`${CARD} flex-1`}>
              <h2 className={CARD_TITLE}>M2 Ports</h2>
              <M2PortTable ports={data.m2_ports} />
            </div>
          </div>
          <div className={`${CARD} flex-1 min-h-0`}>
            <h2 className={CARD_TITLE}>Efficiency A &amp; B — Live</h2>
            <div className="flex-1 min-h-0 relative">
              <LiveChart
                signals={['EfficiencyA', 'EfficiencyB']}
                historyPoints={effAHistory}
                historyPointsB={effBHistory}
              />
            </div>
          </div>
        </div>

        {/* Col 2: Live sensor readings */}
        <div className={`${CARD} w-[31%] shrink-0 min-h-0`}>
          <h2 className={CARD_TITLE}>Live Data</h2>
          <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="grid grid-cols-2 gap-x-4">
            <S title="Sensors" />
            <D label="S1 (Speed)"    value={`${data.s1 ?? 0} RPM`}         vt="rpm" />
            <D label="SP (Setpoint)" value={`${data.sp ?? 0} RPM`}         vt="rpm" />
            <D label="TP (Position)" value={`${tp_pct}%`}                  vt="pct" />
            <D label="T1"            value={`${t1} °F`}                    vt="temp" />
            <D label="T3"            value={`${t3} °F`}                    vt="temp" />
            <D label="F1"            value={`${f1.toFixed(2)} GPM`}        vt="gpm" />
            <D label="F2"            value={`${f2.toFixed(3)} GPM`}        vt="gpm" />
            <D label="F3"            value={`${f3.toFixed(2)} GPM`}        vt="gpm" />
            <D label="P1"            value={`${data.p1 ?? 0} PSI`}         vt="psi" />
            <D label="P2"            value={`${data.p2 ?? 0} PSI`}         vt="psi" />
            <D label="P3"            value={`${data.p3 ?? 0} PSI`}         vt="psi" />
            <D label="P4"            value={`${data.p4 ?? 0} PSI`}         vt="psi" />
            <D label="P5"            value={`${data.p5 ?? 0} PSI`}         vt="psi" />

            <S title="Cycle / Control" />
            <D label="Mode"       value={isAutomatic ? 'Automatic' : 'Manual'} />
            <D label="Step"       value={data.step ?? '—'} />
            <D label="Cycle"      value={data.cycle ?? 0}                  vt="raw" />
            <D label="Timer"      value={`${cycleTimer_s} s`}              vt="raw" />
            <D label="Delay"      value={`${delay_s} s`}                   vt="raw" />
            <D label="LC Setp."   value={`${data.lcSetpoint ?? 0} PSI`}   vt="psi" />
            <D label="LC Reg."    value={<ActiveBadge value={data.lcRegulate} onLabel="Active" offLabel="Off" />} />
            <D label="Trending"   value={<ActiveBadge value={data.trending} onLabel="Yes" offLabel="No" />} />
            <D label="TP Rev."    value={<ActiveBadge value={data.tp_reved} onLabel="Yes" offLabel="No" />} />
            <D label="Dir Switch" value={dirLabel} />

            <S title="Machine State" />
            <D label="Started"   value={<ActiveBadge value={data.started} onLabel="Yes" offLabel="No" />} />
            <D label="Stopped"   value={<ActiveBadge value={data.stopped} onLabel="Yes" offLabel="No" />} />
            <D label="E-Stop"    value={<ActiveBadge value={data.e_stopped} onLabel="Active" offLabel="Clear" />} />
            <D label="Start Btn" value={<ActiveBadge value={data.start_btn} onLabel="Pressed" offLabel="Open" />} />
            <D label="Stop SW"   value={<ActiveBadge value={data.stop_sw} onLabel="Active" offLabel="Open" />} />
            <D label="EStop SW"  value={<ActiveBadge value={data.estop_sw} onLabel="Active" offLabel="Clear" />} />
            <D label="TP FWD"    value={<ActiveBadge value={data.tp_fwd} onLabel="ON" offLabel="OFF" />} />
            <D label="TP REV"    value={<ActiveBadge value={data.tp_rev} onLabel="ON" offLabel="OFF" />} />

            <S title="M1 Outputs" />
            <D label="Sol A"     value={<ActiveBadge value={data.sol_a} onLabel="ON" offLabel="OFF" />} />
            <D label="Sol B"     value={<ActiveBadge value={data.sol_b} onLabel="ON" offLabel="OFF" />} />
            <D label="TP9A En."  value={<ActiveBadge value={data.tp9a_enable} onLabel="On" offLabel="Off" />} />
            <D label="TP9A Dir"  value={<ActiveBadge value={data.tp9a_dir} onLabel="FWD" offLabel="REV" />} />
            <D label="M2 TP9A"   value={<ActiveBadge value={data.m2_tp9a_dir} onLabel="FWD" offLabel="REV" />} />
          </div>
          </div>{/* end scrollable wrapper */}
        </div>

        {/* Col 3: Deep diagnostics */}
        <div className={`${CARD} flex-1 min-h-0`}>
          <h2 className={CARD_TITLE}>Diagnostics</h2>
          <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="grid grid-cols-2 gap-x-4">
            <S title="LC1 Control Loop" />
            <D label="LC1 Actual"    value={data.lc1 ?? '—'}              vt="raw" />
            <D label="LC1 Setpoint"  value={`${data.lcSetpoint ?? 0} PSI`} vt="psi" />
            <D label="LC1 Feedback"  value={data.lc1_feedback ?? '—'}     vt="raw" />
            <D label="LC1 Enable"    value={<ActiveBadge value={data.lc1_enable} onLabel="On" offLabel="Off" />} />
            <D label="LC1 State"     value={data.lc1_state ?? '—'}        vt="raw" />
            <D label="LC1 Regulate"  value={<ActiveBadge value={data.lcRegulate} onLabel="Active" offLabel="Off" />} />

            <S title="SP Circuit" />
            <D label="SP Value"      value={data.sp ?? 0}                  vt="rpm" />
            <D label="SP Feedback"   value={data.sp_feedback ?? '—'}      vt="raw" />
            <D label="SP Enable"     value={<ActiveBadge value={data.sp_enable} onLabel="On" offLabel="Off" />} />
            <D label="SP Regulate"   value={<ActiveBadge value={data.sp_regulate} onLabel="Active" offLabel="Off" />} />
            <D label="SP Rev"        value={<ActiveBadge value={data.sp_rev} onLabel="Yes" offLabel="No" />} />

            <S title="M2 Data" />
            <D label="M2 POT"        value={data.m2_pot ?? '—'}           vt="raw" />
            <D label="M2 TP9A Cmd"   value={data.m2_tp9a ?? '—'}          vt="raw" />

            <S title="Sensor Scale Factors" />
            <D label="T1 Scale"      value={data.ee_t1_scale ?? '—'}      vt="raw" />
            <D label="T3 Scale"      value={data.ee_t3_scale ?? '—'}      vt="raw" />
            <D label="F1 Scale"      value={data.ee_f1_scale ?? '—'}      vt="raw" />
            <D label="F2 Scale"      value={data.ee_f2_scale ?? '—'}      vt="raw" />
            <D label="F3 Scale"      value={data.ee_f3_scale ?? '—'}      vt="raw" />
            <D label="P1 Scale"      value={data.ee_p1_scale ?? '—'}      vt="raw" />
            <D label="P4 Scale"      value={data.ee_p4_scale ?? '—'}      vt="raw" />
            <D label="P5 Scale"      value={data.ee_p5_scale ?? '—'}      vt="raw" />

            <S title="Motor Config" />
            <D label="SM RPM"        value={data.ee_sm_rpm ?? '—'}        vt="rpm" />
            <D label="SM Rate"       value={data.ee_sm_rate ?? '—'}       vt="raw" />
            <D label="SM Timer"      value={data.ee_sm_timer ?? '—'}      vt="raw" />
            <D label="Cycle Delay"   value={data.ee_cycle_delay ?? '—'}   vt="raw" />

            <S title="Cycle Profile" />
            <D label="Time 1"        value={data.ee_cycle_time1 ?? '—'}   vt="raw" />
            <D label="Time 2"        value={data.ee_cycle_time2 ?? '—'}   vt="raw" />
            <D label="Time 3"        value={data.ee_cycle_time3 ?? '—'}   vt="raw" />
            <D label="Time 4"        value={data.ee_cycle_time4 ?? '—'}   vt="raw" />
            <D label="Time 5"        value={data.ee_cycle_time5 ?? '—'}   vt="raw" />
            <D label="PSI 1"         value={data.ee_cycle_psi1 ?? '—'}    vt="psi" />
            <D label="PSI 2"         value={data.ee_cycle_psi2 ?? '—'}    vt="psi" />
            <D label="PSI 3"         value={data.ee_cycle_psi3 ?? '—'}    vt="psi" />
            <D label="PSI 4"         value={data.ee_cycle_psi4 ?? '—'}    vt="psi" />
            <D label="PSI 5"         value={data.ee_cycle_psi5 ?? '—'}    vt="psi" />
          </div>
          </div>{/* end scrollable wrapper */}
        </div>

      </div>

      {/* ── Log Control Bar ── */}
      <div className="flex items-center gap-4 px-3 py-2 border-t border-black/10 shrink-0 dark:border-white/10">
        {/* Log Manual toggle */}
        <button
          onClick={handleLogManualToggle}
          className={`text-xs px-3 py-1.5 rounded-lg font-semibold border transition-colors ${
            data.log_manual
              ? 'bg-teal-100 text-teal-700 border-teal-300 dark:bg-teal-900/60 dark:text-teal-300 dark:border-teal-700/50'
              : 'bg-black/5 text-gray-600 border-black/10 hover:bg-black/10 dark:bg-white/5 dark:text-gray-400 dark:border-white/10 dark:hover:bg-white/10'
          }`}
        >
          {data.log_manual ? '● Log Manual' : '○ Log Manual'}
        </button>

        {/* Row counter — live from WebSocket */}
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Rows added to debug log:{' '}
          <span className="font-bold text-gray-900 dark:text-white tabular-nums">{rowsLogged}</span>
        </span>

        <div className="flex-1" />

        {/* Export */}
        <button
          onClick={handleExport}
          disabled={isExporting}
          className="text-xs bg-[#EB1C23] hover:bg-[#c8171d] disabled:opacity-50 text-white px-4 py-1.5 rounded-lg font-semibold transition-colors"
        >
          {isExporting ? 'Exporting…' : 'Export Debug Data'}
        </button>

        {/* Clear */}
        <button
          onClick={handleClear}
          className="text-xs bg-black/10 hover:bg-black/20 text-gray-700 px-3 py-1.5 rounded-lg font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-gray-300"
        >
          Clear
        </button>
      </div>

    </div>
  )
}
