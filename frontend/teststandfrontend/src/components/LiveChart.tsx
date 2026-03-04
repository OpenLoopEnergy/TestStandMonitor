import { useEffect, useRef } from 'react'
import {
  Chart,
  LineController, LineElement, PointElement,
  LinearScale, TimeScale,
  Filler, Tooltip, Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import type { ChartSignal, LiveData, SignalPoint } from '../types/signals'

Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Tooltip, Legend)

const Y_MAX: Record<ChartSignal, number> = {
  S1: 2000, SP: 2000, TP: 110,
  F1: 200, F2: 32, F3: 200,
  T1: 200, T3: 200,
  P1: 6000, P2: 600, P3: 1000, P4: 100, P5: 6000,
  TheoFlow: 100, Efficiency: 110,
}

interface Props {
  signal: ChartSignal
  liveData: LiveData
  historyPoints: SignalPoint[]
}

export function LiveChart({ signal, liveData, historyPoints }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<Chart | null>(null)

  // Build datasets from either history (for DB signals) or live accumulated points
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const labels = historyPoints.map(p => new Date(p.timestamp))
    const values = historyPoints.map(p => p.value)

    if (!chartRef.current) {
      const ctx = canvas.getContext('2d')!
      const grad = ctx.createLinearGradient(0, 0, 0, 300)
      grad.addColorStop(0, 'rgba(235,28,35,0.5)')
      grad.addColorStop(1, 'rgba(235,28,35,0.02)')

      chartRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: `${signal} Data`,
            data: values,
            borderColor: '#EB1C23',
            backgroundColor: grad,
            borderWidth: 2,
            fill: true,
            pointRadius: 2,
            tension: 0.4,
          }],
        },
        options: {
          animation: false,
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'time',
              time: { unit: 'second' },
              ticks: { color: '#9ca3af', maxTicksLimit: 8 },
              grid: { color: '#374151' },
            },
            y: {
              beginAtZero: true,
              max: Y_MAX[signal] ?? 100,
              ticks: { color: '#9ca3af' },
              grid: { color: '#374151' },
            },
          },
          plugins: {
            legend: { labels: { color: '#f5f5f5' } },
            tooltip: {
              backgroundColor: 'rgba(0,0,0,0.8)',
              titleColor: '#f5f5f5',
              bodyColor: '#f5f5f5',
            },
          },
        },
      })
    } else {
      const chart = chartRef.current
      chart.data.labels = labels
      chart.data.datasets[0].data = values
      chart.data.datasets[0].label = `${signal} Data`
      chart.options.scales!.y = {
        ...chart.options.scales!.y,
        max: Y_MAX[signal] ?? 100,
      }
      chart.update('none')
    }
  }, [signal, historyPoints, liveData])

  // Destroy chart on unmount
  useEffect(() => {
    return () => {
      chartRef.current?.destroy()
      chartRef.current = null
    }
  }, [])

  return (
    <div className="relative h-full w-full">
      <canvas ref={canvasRef} />
    </div>
  )
}
