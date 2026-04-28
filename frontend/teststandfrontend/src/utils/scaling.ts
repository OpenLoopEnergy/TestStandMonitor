export const scaleF1 = (raw: number): number => raw * 0.01
export const scaleT = (raw: number): number => raw * 0.1
export const scaleTp = (raw: number): number => raw / 10.23

export const calcTheoFlow = (s1: number, inputFactor: number): number =>
  inputFactor > 0 ? (s1 * inputFactor) / 231 : 0

export const calcEfficiency = (f1Raw: number, theoFlow: number): number =>
  theoFlow > 0 ? (f1Raw * 0.01 / theoFlow) * 100 : 0
