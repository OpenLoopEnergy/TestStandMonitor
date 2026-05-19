import { describe, it, expect } from 'vitest'
import { scaleF1, scaleT, scaleTp, calcTheoFlow, calcEfficiency } from './scaling'

describe('scaleF1', () => {
  it('converts raw centi-units to GPM', () => {
    expect(scaleF1(250)).toBe(2.5)
  })
  it('returns 0 for zero input', () => {
    expect(scaleF1(0)).toBe(0)
  })
  it('handles negative values', () => {
    expect(scaleF1(-100)).toBe(-1)
  })
})

describe('scaleT', () => {
  it('divides raw temperature by 10', () => {
    expect(scaleT(720)).toBe(72)
  })
  it('returns 0 for zero', () => {
    expect(scaleT(0)).toBe(0)
  })
})

describe('scaleTp', () => {
  it('converts to percentage near 100 for 1023', () => {
    expect(scaleTp(1023)).toBeCloseTo(100.0, 1)
  })
  it('returns 0 for zero', () => {
    expect(scaleTp(0)).toBe(0)
  })
})

describe('calcTheoFlow', () => {
  it('computes theoretical flow correctly', () => {
    expect(calcTheoFlow(1200, 11)).toBeCloseTo(57.14, 1)
  })
  it('returns 0 when inputFactor is 0 (no division by zero)', () => {
    expect(calcTheoFlow(1200, 0)).toBe(0)
  })
  it('returns 0 when s1 is 0', () => {
    expect(calcTheoFlow(0, 11)).toBe(0)
  })
  it('handles cu/cm factor (e.g. 6.75)', () => {
    expect(calcTheoFlow(1200, 6.75)).toBeCloseTo((1200 * 6.75) / 231, 4)
  })
})

describe('calcEfficiency', () => {
  it('returns correct efficiency percentage', () => {
    const theoFlow = calcTheoFlow(1200, 11)
    const eff = calcEfficiency(250, theoFlow)
    const expected = (250 * 0.01 / theoFlow) * 100
    expect(eff).toBeCloseTo(expected, 2)
  })
  it('returns 0 when theoFlow is 0 (no division by zero)', () => {
    expect(calcEfficiency(250, 0)).toBe(0)
  })
  it('returns 0 when f1 is 0', () => {
    const theoFlow = calcTheoFlow(1200, 11)
    expect(calcEfficiency(0, theoFlow)).toBe(0)
  })
  it('returns ~100% at full efficiency (f1 scaled matches theoFlow)', () => {
    const theoFlow = calcTheoFlow(1200, 11)
    const f1RawForFullEfficiency = theoFlow * 100
    expect(calcEfficiency(f1RawForFullEfficiency, theoFlow)).toBeCloseTo(100, 1)
  })
})
