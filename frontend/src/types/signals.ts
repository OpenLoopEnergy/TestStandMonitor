/** M1 port open/short fault flags (CAN ID 0x0CFF110A). 0=OK, 1=Fault. */
export interface M1PortsData {
  sp_open: number; sp_short: number
  sp_enable_open: number; sp_enable_short: number
  sp_rev_open: number; sp_rev_short: number
  tp_open: number; tp_short: number
  tp_enable_open: number; tp_enable_short: number
  tp_rev_open: number; tp_rev_short: number
  lc1_open: number; lc1_short: number
  lc1_pwr_open: number; lc1_pwr_short: number
  led_open: number; led_short: number
  m1_blink: number
}

/** M2 port open/short fault flags + supply voltage (CAN ID 0x0CFF0F14). 0=OK, 1=Fault. */
export interface M2PortsData {
  polarity_open: number; polarity_short: number
  stop_lamp_open: number; stop_lamp_short: number
  sol_a_open: number; sol_a_short: number
  sol_b_open: number; sol_b_short: number
  tp9a_open: number; tp9a_short: number
  tp9a_fwd_open: number; tp9a_fwd_short: number
  tp9a_rev_open: number; tp9a_rev_short: number
  m2_blink: number
  supply_voltage: number  // raw — multiply by 0.0339 for volts
}

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

  // Flows (raw — F1/F2/F3 all use × 0.01 on display)
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

  // Direction / reversal state
  tp_reved: number      // TP output reversed flag
  m2_tp9a_dir: number   // M2 TP9A direction
  ee_dir_switch: number // 0=Both, 1=Forward, 2=Backward

  // Meta
  input_factor?: number
  theo_flow?: number
  efficiency?: number
  pi_connected?: boolean
  debug_mode?: boolean
  log_manual?: boolean

  // Machine state inputs (from 0x0CFF010A)
  started?: number; stopped?: number; e_stopped?: number
  start_btn?: number; stop_sw?: number; estop_sw?: number
  tp_fwd?: number; tp_rev?: number

  // M1 command outputs (from 0x0CFF050A)
  sol_a?: number; sol_b?: number; tp9a_enable?: number; tp9a_dir?: number

  // LC1 control loop (from 0x0CFF020A)
  lc1?: number; lc1_feedback?: number; lc1_enable?: number; lc1_state?: number

  // SP circuit (from 0x0CFF030A)
  sp_feedback?: number; sp_enable?: number; sp_regulate?: number; sp_rev?: number

  // M2 additional (from 0x0CFF0E14)
  m2_pot?: number; m2_tp9a?: number

  // EE motor config (from 0x0CFF070A)
  ee_sm_rpm?: number; ee_sm_rate?: number; ee_sm_timer?: number; ee_cycle_delay?: number

  // EE cycle profile (from 0x0CFF080A / 0x0CFF090A)
  ee_cycle_time1?: number; ee_cycle_time2?: number; ee_cycle_time3?: number
  ee_cycle_time4?: number; ee_cycle_time5?: number
  ee_cycle_psi1?: number; ee_cycle_psi2?: number; ee_cycle_psi3?: number
  ee_cycle_psi4?: number; ee_cycle_psi5?: number

  // Sensor scale factors (from 0x0CFF0A0A / 0x0CFF0B0A)
  ee_t1_scale?: number; ee_t3_scale?: number; ee_f1_scale?: number; ee_f2_scale?: number
  ee_f3_scale?: number; ee_p1_scale?: number; ee_p4_scale?: number; ee_p5_scale?: number

  // CAN frame rate
  pi_fps?: number
  // Debug log row counter (incremented by debug_logger, reset by /clear_debug_table)
  debug_rows_logged?: number

  // Port diagnostics
  m1_ports?: M1PortsData
  m2_ports?: M2PortsData
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
  minEfficiencyPct?: string
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
  | 'TheoFlow' | 'EfficiencyA' | 'EfficiencyB'
