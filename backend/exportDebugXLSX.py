"""
Debug log Excel export — parallel to exportXLSX.py.
Do NOT modify exportXLSX.py; changes to that file affect the standard test export.
"""
import os
import pandas as pd
from backend.time_utils import get_export_now

# Re-use the same brand palette
C_RED         = '#EB1C23'
C_WHITE       = '#FFFFFF'
C_CHARCOAL    = '#2E3E4D'
C_BORDER_DARK = '#1A2733'
C_ROW_EVEN    = '#EBF0F5'

_ASSETS_LOGO   = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
_FALLBACK_LOGO = os.path.join(os.path.dirname(__file__), "..", "frontend", "teststandfrontend", "public", "logo.png")
LOGO_PATH = _ASSETS_LOGO if os.path.isfile(_ASSETS_LOGO) else _FALLBACK_LOGO

# Column display names for each DebugLog attribute
_CORE_COLS = [
    ("Date",        None),
    ("Time",        None),
    ("S1",          "s1"),
    ("SP",          "sp"),
    ("TP",          "tp"),
    ("Cycle",       "cycle"),
    ("Cycle Timer", "cycle_timer"),
    ("LC Setpoint", "lc_setpoint"),
    ("LC Regulate", "lc_regulate"),
    ("Step",        "step"),
    ("F1",          "f1"),        # scaled ×0.01 at export time
    ("F2",          "f2"),
    ("F3",          "f3"),        # scaled ×0.01 at export time
    ("T1",          "t1"),
    ("T3",          "t3"),
    ("P1",          "p1"),
    ("P2",          "p2"),
    ("P3",          "p3"),
    ("P4",          "p4"),
    ("P5",          "p5"),
    ("TP Reversed", "tp_reversed"),
    ("Dir Switch",  "ee_dir_switch"),
    ("Trending",    "trending"),
]

_MACHINE_COLS = [
    ("Started",  "started"),
    ("Stopped",  "stopped"),
    ("E-Stopped","e_stopped"),
]

_M1_CMD_COLS = [
    ("Sol A",       "sol_a"),
    ("Sol B",       "sol_b"),
    ("TP9A Enable", "tp9a_enable"),
    ("TP9A Dir",    "tp9a_dir"),
]

_LOOP_COLS = [
    ("LC1 Actual",   "lc1"),
    ("LC1 Feedback", "lc1_feedback"),
    ("LC1 Enable",   "lc1_enable"),
    ("LC1 State",    "lc1_state"),
    ("SP Feedback",  "sp_feedback"),
    ("SP Enable",    "sp_enable"),
    ("SP Regulate",  "sp_regulate"),
    ("SP Rev",       "sp_rev"),
]

_M2_DATA_COLS = [
    ("M2 POT",      "m2_pot"),
    ("M2 TP9A Cmd", "m2_tp9a"),
    ("M2 TP9A Dir", "m2_tp9a_dir"),
]

_M1_PORT_COLS = [
    ("M1 SP Open",          "m1_sp_open"),
    ("M1 SP Short",         "m1_sp_short"),
    ("M1 SP En Open",       "m1_sp_enable_open"),
    ("M1 SP En Short",      "m1_sp_enable_short"),
    ("M1 SP Rev Open",      "m1_sp_rev_open"),
    ("M1 SP Rev Short",     "m1_sp_rev_short"),
    ("M1 TP Open",          "m1_tp_open"),
    ("M1 TP Short",         "m1_tp_short"),
    ("M1 TP En Open",       "m1_tp_enable_open"),
    ("M1 TP En Short",      "m1_tp_enable_short"),
    ("M1 TP Rev Open",      "m1_tp_rev_open"),
    ("M1 TP Rev Short",     "m1_tp_rev_short"),
    ("M1 LC1 Open",         "m1_lc1_open"),
    ("M1 LC1 Short",        "m1_lc1_short"),
    ("M1 LC1 PWR Open",     "m1_lc1_pwr_open"),
    ("M1 LC1 PWR Short",    "m1_lc1_pwr_short"),
    ("M1 LED Open",         "m1_led_open"),
    ("M1 LED Short",        "m1_led_short"),
    ("M1 Blink",            "m1_blink"),
]

_M2_PORT_COLS = [
    ("M2 Polarity Open",    "m2_polarity_open"),
    ("M2 Polarity Short",   "m2_polarity_short"),
    ("M2 Stop Lamp Open",   "m2_stop_lamp_open"),
    ("M2 Stop Lamp Short",  "m2_stop_lamp_short"),
    ("M2 Sol A Open",       "m2_sol_a_open"),
    ("M2 Sol A Short",      "m2_sol_a_short"),
    ("M2 Sol B Open",       "m2_sol_b_open"),
    ("M2 Sol B Short",      "m2_sol_b_short"),
    ("M2 TP9A Open",        "m2_tp9a_open"),
    ("M2 TP9A Short",       "m2_tp9a_short"),
    ("M2 TP9A FWD Open",    "m2_tp9a_fwd_open"),
    ("M2 TP9A FWD Short",   "m2_tp9a_fwd_short"),
    ("M2 TP9A REV Open",    "m2_tp9a_rev_open"),
    ("M2 TP9A REV Short",   "m2_tp9a_rev_short"),
    ("M2 Blink",            "m2_blink"),
    ("M2 Supply Voltage",   "m2_supply_voltage"),
]

_EE_COLS = [
    ("SM RPM",        "ee_sm_rpm"),
    ("SM Rate",       "ee_sm_rate"),
    ("SM Timer",      "ee_sm_timer"),
    ("Cycle Delay",   "ee_cycle_delay"),
    ("Cycle Time 1",  "ee_cycle_time1"),
    ("Cycle Time 2",  "ee_cycle_time2"),
    ("Cycle Time 3",  "ee_cycle_time3"),
    ("Cycle Time 4",  "ee_cycle_time4"),
    ("Cycle Time 5",  "ee_cycle_time5"),
    ("Cycle PSI 1",   "ee_cycle_psi1"),
    ("Cycle PSI 2",   "ee_cycle_psi2"),
    ("Cycle PSI 3",   "ee_cycle_psi3"),
    ("Cycle PSI 4",   "ee_cycle_psi4"),
    ("Cycle PSI 5",   "ee_cycle_psi5"),
]

_DIR_SWITCH_LABELS = {0: "Both", 1: "Forward", 2: "Backward"}


def process_debug_to_excel(rows: list, metadata: dict, export_dir: str) -> str:
    """
    Build a Debug export Excel file from DebugLog ORM rows.
    Returns the path to the written .xlsx file.
    """
    from datetime import timezone

    now = get_export_now()
    all_cols = (
        _CORE_COLS + _MACHINE_COLS + _M1_CMD_COLS + _LOOP_COLS +
        _M2_DATA_COLS + _M1_PORT_COLS + _M2_PORT_COLS + _EE_COLS
    )

    records = []
    for r in rows:
        row_ts = r.logged_at.astimezone(now.tzinfo) if r.logged_at else now
        raw_f1 = (r.f1 or 0.0) * 0.01
        raw_f3 = (r.f3 or 0.0) * 0.01

        record = {
            "Date":        row_ts.strftime("%Y-%m-%d"),
            "Time":        row_ts.strftime("%H:%M:%S"),
            "S1":          r.s1,        "SP":          r.sp,
            "TP":          r.tp,        "Cycle":       r.cycle,
            "Cycle Timer": r.cycle_timer,
            "LC Setpoint": r.lc_setpoint,
            "LC Regulate": r.lc_regulate,
            "Step":        r.step,
            "F1":          round(raw_f1, 2),
            "F2":          r.f2,
            "F3":          round(raw_f3, 2),
            "T1":          r.t1,        "T3":          r.t3,
            "P1":          r.p1,        "P2":          r.p2,
            "P3":          r.p3,        "P4":          r.p4,
            "P5":          r.p5,
            "TP Reversed": 1 if r.tp_reversed else 0,
            "Dir Switch":  _DIR_SWITCH_LABELS.get(r.ee_dir_switch or 0, str(r.ee_dir_switch)),
            "Trending":    r.trending or 0,
            "Started":     r.started,   "Stopped":     r.stopped,
            "E-Stopped":   r.e_stopped,
            "Sol A":       r.sol_a,     "Sol B":       r.sol_b,
            "TP9A Enable": r.tp9a_enable, "TP9A Dir":  r.tp9a_dir,
            "LC1 Actual":  r.lc1,       "LC1 Feedback": r.lc1_feedback,
            "LC1 Enable":  r.lc1_enable, "LC1 State":  r.lc1_state,
            "SP Feedback": r.sp_feedback, "SP Enable":  r.sp_enable,
            "SP Regulate": r.sp_regulate, "SP Rev":     r.sp_rev,
            "M2 POT":      r.m2_pot,    "M2 TP9A Cmd": r.m2_tp9a,
            "M2 TP9A Dir": r.m2_tp9a_dir,
            # M1 ports
            "M1 SP Open":       r.m1_sp_open,       "M1 SP Short":      r.m1_sp_short,
            "M1 SP En Open":    r.m1_sp_enable_open, "M1 SP En Short":   r.m1_sp_enable_short,
            "M1 SP Rev Open":   r.m1_sp_rev_open,   "M1 SP Rev Short":  r.m1_sp_rev_short,
            "M1 TP Open":       r.m1_tp_open,       "M1 TP Short":      r.m1_tp_short,
            "M1 TP En Open":    r.m1_tp_enable_open, "M1 TP En Short":   r.m1_tp_enable_short,
            "M1 TP Rev Open":   r.m1_tp_rev_open,   "M1 TP Rev Short":  r.m1_tp_rev_short,
            "M1 LC1 Open":      r.m1_lc1_open,      "M1 LC1 Short":     r.m1_lc1_short,
            "M1 LC1 PWR Open":  r.m1_lc1_pwr_open,  "M1 LC1 PWR Short": r.m1_lc1_pwr_short,
            "M1 LED Open":      r.m1_led_open,      "M1 LED Short":     r.m1_led_short,
            "M1 Blink":         r.m1_blink,
            # M2 ports
            "M2 Polarity Open":   r.m2_polarity_open,  "M2 Polarity Short":  r.m2_polarity_short,
            "M2 Stop Lamp Open":  r.m2_stop_lamp_open, "M2 Stop Lamp Short": r.m2_stop_lamp_short,
            "M2 Sol A Open":      r.m2_sol_a_open,     "M2 Sol A Short":     r.m2_sol_a_short,
            "M2 Sol B Open":      r.m2_sol_b_open,     "M2 Sol B Short":     r.m2_sol_b_short,
            "M2 TP9A Open":       r.m2_tp9a_open,      "M2 TP9A Short":      r.m2_tp9a_short,
            "M2 TP9A FWD Open":   r.m2_tp9a_fwd_open,  "M2 TP9A FWD Short":  r.m2_tp9a_fwd_short,
            "M2 TP9A REV Open":   r.m2_tp9a_rev_open,  "M2 TP9A REV Short":  r.m2_tp9a_rev_short,
            "M2 Blink":           r.m2_blink,           "M2 Supply Voltage":  r.m2_supply_voltage,
            # EE config
            "SM RPM":       r.ee_sm_rpm,       "SM Rate":      r.ee_sm_rate,
            "SM Timer":     r.ee_sm_timer,     "Cycle Delay":  r.ee_cycle_delay,
            "Cycle Time 1": r.ee_cycle_time1,  "Cycle Time 2": r.ee_cycle_time2,
            "Cycle Time 3": r.ee_cycle_time3,  "Cycle Time 4": r.ee_cycle_time4,
            "Cycle Time 5": r.ee_cycle_time5,
            "Cycle PSI 1":  r.ee_cycle_psi1,   "Cycle PSI 2":  r.ee_cycle_psi2,
            "Cycle PSI 3":  r.ee_cycle_psi3,   "Cycle PSI 4":  r.ee_cycle_psi4,
            "Cycle PSI 5":  r.ee_cycle_psi5,
        }
        records.append(record)

    df = pd.DataFrame(records, columns=[name for name, _ in all_cols])

    # Calculated columns
    input_factor = float(metadata.get("inputFactor") or 11)
    is_cu_in = "cu/cm" not in str(metadata.get("inputFactorType") or "").lower()

    if is_cu_in:
        df["Theo Flow"] = df["S1"].apply(lambda s: (s * input_factor / 231) if s else 0)
    else:
        df["Theo Flow"] = df["S1"].apply(lambda s: (s * input_factor * 0.0002642) if s else 0)

    def eff_a(row):
        tf = row["Theo Flow"]
        return (row["F1"] / tf) if tf > 0 and row.get("F1", 0) > 0.01 else None

    def eff_b(row):
        tf = row["Theo Flow"]
        return (row["F3"] / tf) if tf > 0 and row.get("F3", 0) > 0.01 else None

    df["Efficiency A"] = df.apply(eff_a, axis=1)
    df["Efficiency B"] = df.apply(eff_b, axis=1)

    # Metadata rows (same 8 fields as standard export)
    meta_rows = [
        ["Program Name",    metadata.get("programName", "")],
        ["Description",     metadata.get("description", "")],
        ["Employee ID",     metadata.get("employeeId", "")],
        ["Comp Set",        metadata.get("compSet", "")],
        ["Input Factor",    input_factor],
        ["Input Factor Type", metadata.get("inputFactorType", "cu/in")],
        ["Serial Number",   metadata.get("serialNumber", "")],
        ["Customer ID",     metadata.get("customerId", "")],
    ]
    offset = len(meta_rows) + 1  # +1 for blank separator row

    timestamp = now.strftime("%m-%d-%Y_%I-%M-%S_%p")
    os.makedirs(export_dir, exist_ok=True)
    excel_path = os.path.join(export_dir, f"Debug_{timestamp}.xlsx")

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        pd.DataFrame(meta_rows).to_excel(writer, index=False, sheet_name="Debug Log", header=False)
        df.to_excel(writer, index=False, sheet_name="Debug Log", startrow=offset)

        workbook  = writer.book
        worksheet = writer.sheets["Debug Log"]

        header_fmt   = workbook.add_format({
            "bold": True, "font_color": C_WHITE, "bg_color": C_CHARCOAL,
            "border": 1, "border_color": C_BORDER_DARK, "text_wrap": True,
        })
        meta_key_fmt = workbook.add_format({"bold": True, "font_color": C_RED})
        even_fmt     = workbook.add_format({"bg_color": C_ROW_EVEN})
        odd_fmt      = workbook.add_format({"bg_color": C_WHITE})
        pct_fmt      = workbook.add_format({"num_format": "0.00%"})

        for col_idx, col_name in enumerate(df.columns):
            worksheet.write(offset, col_idx, col_name, header_fmt)

        for row_idx, row_data in enumerate(meta_rows):
            if row_data:
                worksheet.write(row_idx, 0, row_data[0], meta_key_fmt)

        # Column widths
        df_str = df.astype(str)
        for col_idx, col_name in enumerate(df.columns):
            max_len = df_str[col_name].map(len).max() if len(df) > 0 else 0
            worksheet.set_column(col_idx, col_idx, min(max(len(col_name), max_len) + 2, 30))

        # Percent format for efficiency columns
        for col in ["Efficiency A", "Efficiency B"]:
            if col in df.columns:
                idx = df.columns.get_loc(col)
                worksheet.set_column(idx, idx, 14, pct_fmt)

        # Alternating row colors
        if len(df) > 0:
            data_start = offset + 1
            last_row   = len(df) + offset
            n_cols     = len(df.columns) - 1
            worksheet.conditional_format(
                data_start, 0, last_row, n_cols,
                {"type": "formula", "criteria": "=MOD(ROW(),2)=0", "format": even_fmt}
            )
            worksheet.conditional_format(
                data_start, 0, last_row, n_cols,
                {"type": "formula", "criteria": "=MOD(ROW(),2)=1", "format": odd_fmt}
            )
            worksheet.autofilter(offset, 0, last_row, n_cols)

        if os.path.isfile(LOGO_PATH):
            worksheet.insert_image(0, len(df.columns) + 1, LOGO_PATH,
                                   {"x_scale": 1.0, "y_scale": 1.0, "object_position": 3})

    return excel_path
