/** Raw live data frame pushed by the backend over WebSocket. */
export interface LiveData {
  // Speed / control
  s1: number         // Pump speed (RPM)
  sp: number         // Setpoint (RPM)
  tp: number         // Test pump position (raw, 0–1023 → 0–100%)
  delay: number      // Delay (raw centi-seconds)
  trending: number   // 1 = logging active, 0 = idle

  // Cycle state
  cycle: number
  cycleTimer: number // raw centi-seconds
  lcSetpoint: number // PSI
  lcRegulate: number // boolean 0/1
  step: string       // Human-readable state machine step

  // Temperatures (raw — divide by 10 for °F)
  t1: number
  t3: number

  // Flows (raw — F1 is centi-units, divide by 100; F2/F3 also × 0.01 on display)
  f1: number
  f2: number
  f3: number

  // Pressures (PSI, no scaling needed)
  p1: number
  p2: number
  p3: number
  p4: number
  p5: number

  // Mode: 1 = Automatic, 0 = Manual
  pb4: number

  // Meta
  input_factor?: number
  theo_flow?: number
  efficiency?: number
  pi_connected?: boolean
}

/** A single historical data point for the signal chart. */
export interface SignalPoint {
  timestamp: string
  value: number
}

/** Header / program metadata stored in app_settings. */
export interface HeaderData {
  programName?: string
  description?: string
  compSet?: string
  inputFactor?: string
  inputFactorType?: string
  serialNumber?: string
  employeeId?: string
  customerId?: string
}

/** A row from the data log table. */
export interface LogRow {
  Date: string
  Time: string
  S1: number | null
  SP: number | null
  TP: number | null
  Cycle: number | null
  'Cycle Timer': number | null
  LCSetpoint: number | null
  'LC Regulate': number | null
  Step: string | null
  F1: number | null
  F2: number | null
  F3: number | null
  T1: number | null
  T3: number | null
  P1: number | null
  P2: number | null
  P3: number | null
  P4: number | null
  P5: number | null
}

/** Signals that can be selected for the chart. */
export type ChartSignal =
  | 'S1' | 'SP' | 'TP'
  | 'F1' | 'F2' | 'F3'
  | 'T1' | 'T3'
  | 'P1' | 'P2' | 'P3' | 'P4' | 'P5'
  | 'TheoFlow' | 'Efficiency'
