/**
 * WebSocket hook that connects to /ws/frontend and returns the latest
 * live data frame from the backend.
 *
 * Replaces all setInterval(fetchLiveData, 500) polling from the old app.
 * Reconnects automatically with exponential back-off on disconnect.
 */
import { useEffect, useRef, useState } from 'react'
import type { LiveData } from '../types/signals'

const DEFAULT_DATA: LiveData = {
  s1: 0, sp: 0, tp: 0, delay: 0, trending: 0,
  cycle: 0, cycleTimer: 0, lcSetpoint: 0, lcRegulate: 0, step: '—',
  t1: 0, t3: 0,
  f1: 0, f2: 0, f3: 0,
  p1: 0, p2: 0, p3: 0, p4: 0, p5: 0,
  pb4: 0,
  pi_connected: false,
  debug_mode: false,
}

const WS_URL = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}/ws/frontend`

export function useLiveData() {
  const [data, setData] = useState<LiveData>(DEFAULT_DATA)
  const [connected, setConnected] = useState(false)
  const retryDelay = useRef(1000)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    let cancelled = false

    function connect() {
      if (cancelled) return

      const socket = new WebSocket(WS_URL)
      ws.current = socket

      socket.onopen = () => {
        retryDelay.current = 1000
        setConnected(true)
      }

      socket.onmessage = (event) => {
        try {
          const frame = JSON.parse(event.data) as Partial<LiveData>
          setData(prev => ({ ...prev, ...frame }))
        } catch {
          // ignore malformed frames
        }
      }

      socket.onclose = () => {
        setConnected(false)
        if (!cancelled) {
          setTimeout(connect, retryDelay.current)
          retryDelay.current = Math.min(retryDelay.current * 2, 30_000)
        }
      }

      socket.onerror = () => socket.close()
    }

    connect()

    return () => {
      cancelled = true
      ws.current?.close()
    }
  }, [])

  return { data, connected }
}
