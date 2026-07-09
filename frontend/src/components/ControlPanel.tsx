import { useState } from 'react'
import type { LiveData } from '../types/signals'

type Action = 'start' | 'stop' | 'estop'

interface ControlPanelProps {
  data: LiveData
  piConnected: boolean
  isAdmin: boolean
  onToast: (type: 'success' | 'error', msg: string) => void
}

const ACTION_LABELS: Record<Action, string> = {
  start: 'Start',
  stop: 'Stop',
  estop: 'Emergency Stop',
}

/**
 * Admin control panel — issues Start / Stop / Emergency-Stop commands to the
 * stand. Each command requires a confirmation modal. The buttons "light up"
 * from the live decoded signals (not from what was clicked here), so pressing
 * the physical panel button lights the matching button too.
 */
export function ControlPanel({ data, piConnected, onToast }: ControlPanelProps) {
  const [pending, setPending] = useState<Action | null>(null)
  const [busy, setBusy] = useState(false)

  // Command issuing is temporarily disabled — everyone (including admins) can see
  // the live Start/Stop/E-Stop state (via `lit` below) but nobody can click to send
  // a command right now. To re-enable, restore: isAdmin && piConnected && !busy
  const canControl = false

  // Lit state comes from the live frame. Start/Stop use the latched machine-state
  // bit OR their momentary (normally-open) input switch, so a physical press also
  // flashes the button. E-Stop uses ONLY the E_Stopped state bit (Byte 7 bit 4):
  // the eStop_sw input is normally-closed (reads 1 when NOT pressed), so including
  // it would keep the button lit permanently.
  const startLit = !!(data.started || data.start_btn)
  const stopLit = !!(data.stopped || data.stop_sw)
  const estopLit = !!data.e_stopped

  async function send(action: Action) {
    setBusy(true)
    try {
      const res = await fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? 'Command failed')
      }
      onToast('success', `${ACTION_LABELS[action]} command sent.`)
    } catch (e) {
      onToast('error', `${ACTION_LABELS[action]} failed: ${e instanceof Error ? e.message : e}`)
    } finally {
      setBusy(false)
      setPending(null)
    }
  }

  // base + lit/unlit styling per button. Dim only when the Pi is offline so the
  // lit state stays fully visible to non-admins (who just can't click).
  const btn = (lit: boolean, litClasses: string, idleClasses: string) =>
    `flex-1 px-2 py-1.5 rounded-md text-xs font-bold border transition-colors ${
      lit ? litClasses : idleClasses
    } ${!piConnected ? 'opacity-40' : ''} ${canControl ? '' : 'cursor-not-allowed'}`

  return (
    <div className="shrink-0">
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-1 dark:text-white/50">Control</p>
      <div className="flex gap-1.5">
        <button
          disabled={!canControl}
          onClick={() => setPending('start')}
          className={btn(
            startLit,
            'bg-green-600 text-white border-green-400 ring-2 ring-green-400/60 shadow',
            'bg-green-700/10 text-green-700 border-green-700/30 hover:bg-green-700/20 dark:text-green-300 dark:border-green-500/30',
          )}
        >
          {startLit ? '● Start' : 'Start'}
        </button>
        <button
          disabled={!canControl}
          onClick={() => setPending('stop')}
          className={btn(
            stopLit,
            'bg-amber-500 text-white border-amber-300 ring-2 ring-amber-400/60 shadow',
            'bg-amber-600/10 text-amber-700 border-amber-600/30 hover:bg-amber-600/20 dark:text-amber-300 dark:border-amber-500/30',
          )}
        >
          {stopLit ? '● Stop' : 'Stop'}
        </button>
        <button
          disabled={!canControl}
          onClick={() => setPending('estop')}
          className={btn(
            estopLit,
            'bg-red-600 text-white border-red-400 ring-2 ring-red-400/70 shadow',
            'bg-red-700/10 text-red-700 border-red-700/30 hover:bg-red-700/20 dark:text-red-300 dark:border-red-500/30',
          )}
        >
          {estopLit ? '● E-Stop' : 'E-Stop'}
        </button>
      </div>
      {!piConnected ? (
        <p className="text-[9px] text-gray-400 mt-0.5 leading-tight">Pi offline — controls disabled</p>
      ) : (
        <p className="text-[9px] text-gray-400 mt-0.5 leading-tight">Live status — command issuing is temporarily disabled</p>
      )}

      {/* Confirmation modal */}
      {pending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <div className={`text-center mb-1 text-xs font-bold uppercase tracking-widest ${
              pending === 'estop' ? 'text-red-600 dark:text-red-400'
                : pending === 'stop' ? 'text-amber-600 dark:text-amber-400'
                : 'text-green-600 dark:text-green-400'
            }`}>
              {pending === 'estop' ? 'Emergency Stop' : pending === 'stop' ? 'Stop' : 'Start'} Command
            </div>
            <h2 className="text-xl font-bold text-center mb-2 text-gray-900 dark:text-white">
              Send {ACTION_LABELS[pending]} to the stand?
            </h2>
            <p className="text-sm text-gray-600 text-center mb-6 dark:text-gray-400">
              {pending === 'estop'
                ? 'This immediately commands an emergency stop on the test stand.'
                : pending === 'stop'
                ? 'This commands the test stand to stop.'
                : 'This commands the test stand to start.'}
            </p>
            <div className="flex gap-3">
              <button
                disabled={busy}
                onClick={() => send(pending)}
                className={`flex-1 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
                  pending === 'estop' ? 'bg-red-700 hover:bg-red-600'
                    : pending === 'stop' ? 'bg-amber-600 hover:bg-amber-500'
                    : 'bg-green-700 hover:bg-green-600'
                }`}
              >
                {busy ? 'Sending…' : `Send ${ACTION_LABELS[pending]}`}
              </button>
              <button
                disabled={busy}
                onClick={() => setPending(null)}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-900 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
