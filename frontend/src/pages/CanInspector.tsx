import { useEffect } from 'react'
import { useLiveData } from '../hooks/useLiveData'
import { ThemeToggle } from '../components/ThemeToggle'

const ADMIN_KEY = 'teststand_admin'

// Friendly names for known CAN IDs (mirrors pi/can_decoder.py TABLE_NAME_MAP).
const ID_NAMES: Record<string, string> = {
  '0CFF000A': 'FloPSI',
  '0CFF010A': 'TempDigSet (digital inputs)',
  '0CFF020A': 'M1_OutputLC1',
  '0CFF030A': 'M1_OutputSP',
  '0CFF040A': 'M1Timers',
  '0CFF050A': 'M1_Commands',
  '0CFF060A': 'Set_ID',
  '0CFF070A': 'Set_SM',
  '0CFF080A': 'Set_CycleA',
  '0CFF090A': 'Set_CycleB',
  '0CFF0A0A': 'Set_ScaleT',
  '0CFF0B0A': 'Set_ScaleF',
  '0CFF0C0A': 'Scaled_M2_Data',
  '0CFF0D14': 'M2_Data1',
  '0CFF0E14': 'M2_Data2',
  '0CFF110A': 'M1Ports',
  '0CFF0F14': 'M2Ports',
}

// Bit labels for the digital-input message, byte 4 and byte 7 (from the decoder).
// These are the candidates for Start / Stop / E-Stop. Watch which one flips when
// the matching physical button is pressed.
const DIGIN_ID = '0CFF010A'
const DIGIN_BITS: Record<number, [string, string, string, string, string, string, string, string]> = {
  // byte index → labels for bit0..bit7
  4: ['Start', 'Stop_sw', 'PB4 (mode)', 'eStop_sw', 'TP_FWD', 'TP_REV', 'LED', 'Logging'],
  7: ['TP_Enabled', 'TP_Reved', 'Started', 'Stopped', 'E_Stopped', 'bit5', 'bit6', 'bit7'],
}

function byteToBits(b: number): number[] {
  // returns [bit0, bit1, ... bit7] (LSB first)
  return Array.from({ length: 8 }, (_, i) => (b >> i) & 1)
}

export default function CanInspector() {
  useEffect(() => {
    if (sessionStorage.getItem(ADMIN_KEY) !== 'true') window.location.replace('/')
  }, [])

  const { data, connected, piConnected } = useLiveData()
  const canRaw = data.can_raw ?? {}

  const ids = Object.keys(canRaw).sort()
  const digin = canRaw[DIGIN_ID]

  // A value cell flashes when it changes: we re-`key` it by its current value so
  // React remounts it and the one-shot `.cell-flash` CSS animation replays. This
  // keeps the component pure (no refs/clock reads during render).

  return (
    <div className="min-h-screen bg-white text-gray-900 dark:bg-[#1a1a1a] dark:text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/10 dark:border-white/10">
        <div>
          <span className="text-lg font-bold tracking-tight">CAN Bus Inspector</span>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Live raw bytes per CAN ID — press a physical button and watch which bit changes
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${connected ? 'bg-green-100 text-green-700 dark:bg-green-800/60 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300'}`}>
            {connected ? '● Backend' : '○ Backend'}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full font-medium ${piConnected ? 'bg-green-100 text-green-700 dark:bg-green-800/60 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/60 dark:text-red-300'}`}>
            {piConnected ? '● Pi' : '○ Pi'}
          </span>
          <ThemeToggle />
          <a href="/debug" className="text-xs bg-black/10 hover:bg-black/20 px-3 py-1.5 rounded-lg dark:bg-white/10 dark:hover:bg-white/20">← Debug</a>
          <a href="/" className="text-xs bg-black/10 hover:bg-black/20 px-3 py-1.5 rounded-lg dark:bg-white/10 dark:hover:bg-white/20">Dashboard</a>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* ── Focused decode of the digital-input message ── */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wide mb-2">
            Control candidates — {ID_NAMES[DIGIN_ID]} (0x{DIGIN_ID})
          </h2>
          {!digin ? (
            <p className="text-sm text-gray-500">Waiting for message 0x{DIGIN_ID}…</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[4, 7].map(byteIdx => (
                <div key={byteIdx} className="bg-black/[0.03] border border-black/10 rounded-xl p-3 dark:bg-white/[0.03] dark:border-white/10">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Byte {byteIdx}</span>
                    <span key={digin[byteIdx] ?? 0} className="cell-flash font-mono text-xs px-2 py-0.5 rounded bg-black/10 dark:bg-white/10">
                      0x{(digin[byteIdx] ?? 0).toString(16).padStart(2, '0').toUpperCase()}
                    </span>
                  </div>
                  <table className="w-full text-sm">
                    <tbody>
                      {byteToBits(digin[byteIdx] ?? 0).map((bit, i) => (
                        <tr key={i} className="border-b border-black/5 last:border-0 dark:border-white/5">
                          <td className="py-1 text-gray-400 font-mono text-xs w-12">bit{i}</td>
                          <td className="py-1 text-gray-700 dark:text-gray-200">{DIGIN_BITS[byteIdx][i]}</td>
                          <td className="py-1 text-right">
                            <span className={`inline-block w-7 text-center font-mono font-bold rounded ${bit ? 'bg-green-500 text-white' : 'bg-black/10 text-gray-500 dark:bg-white/10'}`}>
                              {bit}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
          <p className="text-xs text-gray-500 mt-2">
            Press the physical <b>Start</b>, <b>Stop</b>, then <b>E-Stop</b> one at a time. Note which bit turns green (1) for each.
            A normally-closed switch (common for E-Stop) reads <b>1</b> when <i>not</i> pressed and <b>0</b> when pressed — that's an inverted signal.
          </p>
        </section>

        {/* ── All CAN IDs, raw ── */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wide mb-2">All messages ({ids.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-black/10 dark:border-white/10 text-gray-400">
                  <th className="text-left py-2 pr-3">CAN ID</th>
                  <th className="text-left py-2 pr-3">Name</th>
                  {Array.from({ length: 8 }, (_, i) => (
                    <th key={i} className="text-center py-2 px-1 font-mono">B{i}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ids.map(id => {
                  const bytes = canRaw[id]
                  return (
                    <tr key={id} className="border-b border-black/5 dark:border-white/5">
                      <td className="py-1.5 pr-3 font-mono font-bold">0x{id}</td>
                      <td className="py-1.5 pr-3 text-gray-500">{ID_NAMES[id] ?? <span className="italic">unknown</span>}</td>
                      {bytes.map((b, i) => (
                        <td key={i} className="text-center px-1 py-1.5">
                          <span
                            key={b}
                            className="cell-flash inline-block font-mono rounded px-1"
                            title={`0b${b.toString(2).padStart(8, '0')}`}
                          >
                            {b.toString(2).padStart(8, '0')}
                          </span>
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Bytes shown as binary (bit7…bit0). A byte highlights yellow for ~1s when it changes — press a button and look for the flash to find the right message and bit.
          </p>
        </section>
      </div>
    </div>
  )
}
