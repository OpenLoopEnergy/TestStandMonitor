import { useEffect, useRef } from 'react'
import {
  Chart,
  LineController, LineElement, PointElement,
  LinearScale, TimeScale,
  Filler, Tooltip, Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import type { ChartSignal, SignalPoint } from '../types/signals'

Chart.register(LineController, LineElement, PointElement, LinearScale, TimeScale, Filler, Tooltip, Legend)

const Y_MAX: Record<ChartSignal, number> = {
  S1: 2000, SP: 2000, TP: 110,
  F1: 200, F2: 32, F3: 200,
  T1: 200, T3: 200,
  P1: 6000, P2: 600, P3: 1000, P4: 100, P5: 6000,
  TheoFlow: 100, EfficiencyA: 110, EfficiencyB: 110,
}

const SIGNAL_COLOR: Partial<Record<ChartSignal, string>> = {
  EfficiencyA: '#EB1C23',
  EfficiencyB: '#3b82f6',
}
const DEFAULT_COLOR = '#EB1C23'

function signalDisplayName(s: ChartSignal): string {
  if (s === 'EfficiencyA') return 'Efficiency A'
  if (s === 'EfficiencyB') return 'Efficiency B'
  return s
}

// Minimal shape we mutate on the Chart.js options objects
type ScaleOpts = { ticks: { color: string }; grid: { color: string }; max?: number }
type TooltipOpts = {
  backgroundColor: string; titleColor: string; bodyColor: string
  borderColor: string; borderWidth: number
}
type PluginOpts = { legend: { display: boolean; labels: { color: string } }; tooltip: TooltipOpts }

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
  signals: ChartSignal[]
  historyPoints: SignalPoint[]
  historyPointsB?: SignalPoint[]  // only supplied when two efficiency signals are selected
}

export function LiveChart({ signals, historyPoints, historyPointsB }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<Chart | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const isDual = signals.length > 1

    // Rebuild when dataset count changes (single ↔ dual)
    if (chartRef.current && chartRef.current.data.datasets.length !== signals.length) {
      chartRef.current.destroy()
      chartRef.current = null
    }

    const c = getChartColors()
    const yMax = Math.max(...signals.map(s => Y_MAX[s] ?? 100))

    if (!chartRef.current) {
      const ctx = canvas.getContext('2d')!

      const datasets = signals.map((sig, i) => {
        const color = SIGNAL_COLOR[sig] ?? DEFAULT_COLOR
        const pts = i === 0 ? historyPoints : (historyPointsB ?? [])
        const values = pts.map(p => p.value)

        if (!isDual) {
          // Single signal: gradient fill (existing look)
          const grad = ctx.createLinearGradient(0, 0, 0, 300)
          grad.addColorStop(0, 'rgba(235,28,35,0.5)')
          grad.addColorStop(1, 'rgba(235,28,35,0.02)')
          return {
            label: signalDisplayName(sig),
            data: values,
            borderColor: color,
            backgroundColor: grad,
            borderWidth: 2,
            fill: true,
            pointRadius: 2,
            tension: 0.4,
          }
        }

        // Dual signal: solid lines, no fill so they don't obscure each other
        return {
          label: signalDisplayName(sig),
          data: values,
          borderColor: color,
          backgroundColor: `${color}1a`,
          borderWidth: 2,
          fill: false,
          pointRadius: 2,
          tension: 0.4,
        }
      })

      const labels = historyPoints.map(p => new Date(p.timestamp))

      chartRef.current = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
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
              max: yMax,
              ticks: { color: c.tick },
              grid:  { color: c.grid },
            },
          },
          plugins: {
            legend: { display: isDual, labels: { color: c.legend } },
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
      chart.data.labels = historyPoints.map(p => new Date(p.timestamp))
      chart.data.datasets[0].data = historyPoints.map(p => p.value)
      chart.data.datasets[0].label = signalDisplayName(signals[0])
      if (isDual && chart.data.datasets[1] && historyPointsB) {
        chart.data.datasets[1].data = historyPointsB.map(p => p.value)
        chart.data.datasets[1].label = signalDisplayName(signals[1])
      }
      const scales = chart.options.scales as unknown as Record<string, ScaleOpts>
      if (scales['y']) scales['y'].max = yMax
      applyChartColors(chart)
    }
  }, [signals, historyPoints, historyPointsB])

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
