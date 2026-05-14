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

// Minimal shape we mutate on the Chart.js options objects
type ScaleOpts = { ticks: { color: string }; grid: { color: string }; max?: number }
type TooltipOpts = {
  backgroundColor: string; titleColor: string; bodyColor: string
  borderColor: string; borderWidth: number
}
type PluginOpts = { legend: { labels: { color: string } }; tooltip: TooltipOpts }

function getChartColors() {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    tick:          isDark ? '#9ca3af' : '#6b7280',
    grid:          isDark ? '#374151' : '#d1d5db',
    legend:        isDark ? '#f5f5f5' : '#111827',
    tooltipBg:     isDark ? 'rgba(0,0,0,0.85)'         : 'rgba(255,255,255,0.97)',
    tooltipTitle:  isDark ? '#f5f5f5'                   : '#111827',
    tooltipBody:   isDark ? '#d1d5db'                   : '#374151',
    tooltipBorder: isDark ? 'rgba(255,255,255,0.1)'     : 'rgba(0,0,0,0.12)',
  }
}

function applyChartColors(chart: Chart) {
  const c = getChartColors()
  const scales = chart.options.scales as unknown as Record<string, ScaleOpts>
  const plugins = chart.options.plugins as unknown as PluginOpts

  if (scales['x']) { scales['x'].ticks.color = c.tick;  scales['x'].grid.color = c.grid }
  if (scales['y']) { scales['y'].ticks.color = c.tick;  scales['y'].grid.color = c.grid }

  plugins.legend.labels.color     = c.legend
  plugins.tooltip.backgroundColor = c.tooltipBg
  plugins.tooltip.titleColor      = c.tooltipTitle
  plugins.tooltip.bodyColor       = c.tooltipBody
  plugins.tooltip.borderColor     = c.tooltipBorder
  plugins.tooltip.borderWidth     = 1
  chart.update('none')
}

interface Props {
  signal: ChartSignal
  liveData: LiveData
  historyPoints: SignalPoint[]
}

export function LiveChart({ signal, liveData, historyPoints }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<Chart | null>(null)

  // Create or update chart data
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const labels = historyPoints.map(p => new Date(p.timestamp))
    const values = historyPoints.map(p => p.value)
    const c = getChartColors()

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
              ticks: { color: c.tick, maxTicksLimit: 8 },
              grid:  { color: c.grid },
            },
            y: {
              beginAtZero: true,
              max: Y_MAX[signal] ?? 100,
              ticks: { color: c.tick },
              grid:  { color: c.grid },
            },
          },
          plugins: {
            legend: { labels: { color: c.legend } },
            tooltip: {
              backgroundColor: c.tooltipBg,
              titleColor:      c.tooltipTitle,
              bodyColor:       c.tooltipBody,
              borderColor:     c.tooltipBorder,
              borderWidth:     1,
            },
          },
        },
      })
    } else {
      const chart = chartRef.current
      chart.data.labels = labels
      chart.data.datasets[0].data = values
      chart.data.datasets[0].label = `${signal} Data`
      const scales = chart.options.scales as unknown as Record<string, ScaleOpts>
      if (scales['y']) scales['y'].max = Y_MAX[signal] ?? 100
      applyChartColors(chart)
    }
  }, [signal, historyPoints, liveData])

  // Recolor immediately when dark/light class changes on <html>
  useEffect(() => {
    const observer = new MutationObserver(() => {
      if (chartRef.current) applyChartColors(chartRef.current)
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

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
