import pandas as pd
import io
import csv
import os
from backend.time_utils import get_export_now

# Primary logo setup
_ASSETS_LOGO   = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
_FALLBACK_LOGO = os.path.join(os.path.dirname(__file__), "..", "frontend", "teststandfrontend", "public", "logo.png")
LOGO_PATH = _ASSETS_LOGO if os.path.isfile(_ASSETS_LOGO) else _FALLBACK_LOGO

# ── Brand Palette & Semantic Styles ──────────────────────────────────────────
C_RED         = '#EB1C23'   # Open Loop Red
C_BLACK       = '#000000'
C_WHITE       = '#FFFFFF'
C_CHARCOAL    = '#2E3E4D'
C_AMBER       = '#ECA400'   # LC Setpoint Target

C_PRESS_P1    = '#4472C4'   # Office Blue
C_PRESS_P5    = '#1B6B8A'   # Teal
C_EFF_FWD     = '#00FFFF'   # Bright Cyan (Forward - Sensor 1)
C_EFF_REV     = '#EB1C23'   # Logo Red (Reverse - Sensor 3)

C_BORDER_DARK = '#1A2733'   # Header borders
C_ROW_EVEN    = '#EBF0F5'   # Alternating row color
C_GRIDLINE    = '#3D5166'   # Grid lines in the dark chart
C_PLOT_BG     = '#0D1421'   # The "Inner" area of the chart


def process_csv_to_excel_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as csv_file:
            file_contents = csv_file.read()

        header_keywords = ["Program Name", "Description", "Employee ID", "Comp Set",
                           "Input Factor", "Input Factor Type", "Serial Number", "Customer ID"]
        float_fields = ["Input Factor", "Serial Number", "Employee ID", "Comp Set", "Customer ID"]
        metadata, data_lines, header_row_found, metadata_row_indices = [], [], False, {}

        reader = csv.reader(io.StringIO(file_contents))
        for row in reader:
            if not row: continue
            if not header_row_found and len(row) >= 2 and any(k in row[0] for k in header_keywords):
                metadata.append(row)
                field_name = row[0].strip()
                if field_name in float_fields:
                    try:
                        metadata[-1][1] = float("".join(c for c in row[1].strip() if c.isdigit() or c == "."))
                    except Exception:
                        metadata[-1][1] = 0.0
                metadata_row_indices[field_name] = len(metadata)
            elif "Time" in row and "S1" in row:
                header_row_found = True
                data_lines.append(row)
            elif header_row_found:
                data_lines.append(row)

        if not header_row_found:
            raise ValueError("Failed to find the data header row.")

        # Ensure core columns are numeric
        df = pd.read_csv(io.StringIO("\n".join([",".join(map(str, row)) for row in data_lines])))

        for col in ["TP", "S1", "F1", "F3", "LCSetpoint", "P1", "P5", "TP Reversed", "Trending"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        def column_letter(idx: int) -> str:
            letter = ""
            while idx >= 0:
                letter = chr(ord("A") + idx % 26) + letter
                idx = idx // 26 - 1
            return letter

        # Column mapping
        S1_letter      = column_letter(df.columns.get_loc("S1"))
        F1_letter      = column_letter(df.columns.get_loc("F1"))
        F3_letter      = column_letter(df.columns.get_loc("F3"))
        B_letter       = column_letter(df.columns.get_loc("Time"))
        U_letter       = column_letter(df.columns.get_loc("TP Reversed")) if "TP Reversed" in df.columns else None
        T_trend_letter = column_letter(df.columns.get_loc("Trending"))    if "Trending"    in df.columns else None
        H_lc_letter    = column_letter(df.columns.get_loc("LCSetpoint"))  if "LCSetpoint"  in df.columns else None
        P1_letter      = column_letter(df.columns.get_loc("P1"))          if "P1"          in df.columns else None
        P5_letter      = column_letter(df.columns.get_loc("P5"))          if "P5"          in df.columns else None

        input_factor_row = metadata_row_indices.get("Input Factor", 5)
        offset = len(metadata) + 1

        # Detect Input Factor type
        is_cu_in = True
        for r in metadata:
            if r and str(r[0]).strip() == "Input Factor Type":
                if "cu/cm" in str(r[1]).strip().lower(): is_cu_in = False
                break

        # 1. Theoretical Flow (Calculation Reference)
        def calculate_theo_flow(row):
            rn = row.name + offset + 2
            if is_cu_in:
                return f"=$B${input_factor_row}*{S1_letter}{rn}/231"
            return f"=$B${input_factor_row}*{S1_letter}{rn}*0.0002642"

        df["Theo Flow"] = df.apply(calculate_theo_flow, axis=1)
        FTheo_L = column_letter(df.columns.get_loc("Theo Flow"))

        # 2. Raw Efficiencies
        def raw_eff_f1(row):
            rn = row.name + offset + 2
            expr = f"{F1_letter}{rn}/{FTheo_L}{rn}"
            return f"=IFERROR(IF({expr}<0.1,NA(),{expr}),NA())"

        def raw_eff_f3(row):
            rn = row.name + offset + 2
            expr = f"{F3_letter}{rn}/{FTheo_L}{rn}"
            return f"=IFERROR(IF({expr}<0.1,NA(),{expr}),NA())"

        df["EffRaw_F1"] = df.apply(raw_eff_f1, axis=1)
        df["EffRaw_F3"] = df.apply(raw_eff_f3, axis=1)
        W1_L = column_letter(df.columns.get_loc("EffRaw_F1"))
        W3_L = column_letter(df.columns.get_loc("EffRaw_F3"))

        # 3. Efficiency A (Fwd/F1) and B (Rev/F3)
        if U_letter and T_trend_letter:
            def eff_a_formula(row):
                rn = row.name + offset + 2
                prev = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=1,${U_letter}{prev}=1)),${W1_L}{rn},NA())'

            def eff_b_formula(row):
                rn = row.name + offset + 2
                prev = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=0,${U_letter}{prev}=0)),${W3_L}{rn},NA())'

            df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
            df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

        # --- Excel Export ---
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")
        FORMULA_COLS = {"Theo Flow", "EffRaw_F1", "EffRaw_F3", "Efficiency A", "Efficiency B"}

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            pd.DataFrame(metadata).to_excel(writer, index=False, sheet_name="Data", header=False)
            df.to_excel(writer, index=False, sheet_name="Data", startrow=offset)
            workbook, worksheet = writer.book, writer.sheets["Data"]

            # ── Formats ─────────────────────────────────────────────────────
            percent_fmt = workbook.add_format({"num_format": "0.00%"})
            header_fmt  = workbook.add_format({"bold": True, "font_color": C_WHITE, "bg_color": C_CHARCOAL, "border": 1, "border_color": C_BORDER_DARK})
            meta_key_fmt = workbook.add_format({"bold": True, "font_color": C_RED})
            even_fmt    = workbook.add_format({"bg_color": C_ROW_EVEN})
            odd_fmt     = workbook.add_format({"bg_color": C_WHITE})

            # Headers and Metadata labels
            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(offset, col_idx, col_name, header_fmt)

            # ── Metadata key labels ─────────────────────────────────────────
            for row_idx, row_data in enumerate(metadata):
                if row_data: worksheet.write(row_idx, 0, row_data[0], meta_key_fmt)

            # Deep Auto-fit
            df_str = df.astype(str)
            for col_idx, col_name in enumerate(df.columns):
                max_data_len = df_str[col_name].map(len).max() if len(df) > 0 else 0
                col_width = max(len(col_name), max_data_len) + 2
                if col_idx == 0: col_width = max(col_width, max((len(str(r[0])) for r in metadata if r), default=0) + 2)
                worksheet.set_column(col_idx, col_idx, min(col_width, 40))

            # Apply percent formatting
            for col in ["EffRaw_F1", "EffRaw_F3", "Efficiency A", "Efficiency B"]:
                if col in df.columns:
                    idx = df.columns.get_loc(col)
                    worksheet.set_column(idx, idx, 14, percent_fmt)

            # ── Alternating row colours ─────────────────────────────────────
            last_row, data_start = len(df) + offset + 1, offset + 1
            worksheet.conditional_format(data_start, 0, last_row, len(df.columns)-1, {"type": "formula", "criteria": "=MOD(ROW(),2)=0", "format": even_fmt})
            worksheet.conditional_format(data_start, 0, last_row, len(df.columns)-1, {"type": "formula", "criteria": "=MOD(ROW(),2)=1", "format": odd_fmt})
            worksheet.autofilter(offset, 0, last_row, len(df.columns)-1)

            if os.path.isfile(LOGO_PATH):
                worksheet.insert_image(0, 9, LOGO_PATH, {"x_scale": 1.0, "y_scale": 1.0, "object_position": 3})

            # ── Chart Logic ──────────────────────────────────────────────────
            if len(df) > 0:
                first_row, chart_last = offset + 2, len(df) + offset + 1
                def time_cats(): return f"=Data!${B_letter}${first_row}:${B_letter}${chart_last}"

                # 1. PRIMARY Chart (Pressure Areas & LC Line on Left Axis)
                chart = workbook.add_chart({"type": "area"})

                # P5 Background
                chart.add_series({
                    "name": "P5 Pressure", "categories": time_cats(),
                    "values": f"=Data!${P5_letter}${first_row}:${P5_letter}${chart_last}",
                    "fill": {"color": C_PRESS_P5, "transparency": 20}, "border": {"none": True},
                })
                # P1 Background
                chart.add_series({
                    "name": "P1 Pressure", "categories": time_cats(),
                    "values": f"=Data!${P1_letter}${first_row}:${P1_letter}${chart_last}",
                    "fill": {"color": C_PRESS_P1, "transparency": 20}, "border": {"none": True},
                })

                # LC Setpoint (Combined as a Line on the Left Axis)
                if H_lc_letter:
                    lc_line = workbook.add_chart({"type": "line"})
                    lc_line.add_series({
                        "name": "LC Setpoint", "categories": time_cats(),
                        "values": f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${chart_last}",
                        "line": {"color": C_AMBER, "width": 2, "dash_type": "dash"},
                    })
                chart.combine(lc_line)

                # 2. SECONDARY Chart (Efficiency as Columns on Right Axis)
                # This fixes the scaling and the "connecting across gaps" issue
                eff_col_chart = workbook.add_chart({"type": "column"})

                # Efficiency A (F1)
                col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                eff_col_chart.add_series({
                    "name": "Fwd Efficiency (F1)",
                    "values": f"=Data!${col_ea}${first_row}:${col_ea}${chart_last}",
                    "fill": {"color": C_EFF_FWD, "transparency": 60},
                    "y2_axis": True,
                })
                # Efficiency B (F3)
                col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                eff_col_chart.add_series({
                    "name": "Rev Efficiency (F3)",
                    "values": f"=Data!${col_eb}${first_row}:${col_eb}${chart_last}",
                    "fill": {"color": C_EFF_REV, "transparency": 60},
                    "y2_axis": True,
                })
                chart.combine(eff_col_chart)

                # 3. DARK THEME & AXIS STYLING (Applied to the main object)
                chart.set_chartarea({"fill": {"color": C_BLACK}, "border": {"none": True}})
                chart.set_plotarea( {"fill": {"color": C_PLOT_BG}, "border": {"none": True}})
                chart.set_title({"name": "Open Loop Pump Test Profile", "name_font": {"color": C_RED, "size": 16, "bold": True}})

                # Bottom Axis
                chart.set_x_axis({
                    "name": "Time Index",
                    "name_font": {"color": C_WHITE}, "num_font": {"color": C_WHITE},
                    "line": {"color": C_WHITE}
                })

                # LEFT Axis (PSI)
                chart.set_y_axis({
                    "name": "Pressure (PSI)",
                    "name_font": {"color": C_WHITE}, "num_font": {"color": C_WHITE},
                    "min": 0, "max": 3500,
                    "major_gridlines": {"visible": True, "line": {"color": C_GRIDLINE}},
                    "line": {"color": C_WHITE}
                })

                # RIGHT Axis (Efficiency %)
                # Explicitly setting the y2 axis properties on the main chart forces the white labels
                chart.set_y2_axis({
                    "name": "Efficiency %",
                    "name_font": {"color": C_WHITE}, "num_font":  {"color": C_WHITE},
                    "min": 0, "max": 1.1, "major_unit": 0.2,
                    "num_format": "0%", "line": {"color": C_WHITE},
                    "visible": True
                })

                chart.set_legend({"position": "bottom", "font": {"color": C_WHITE}})
                chartsheet = workbook.add_chartsheet("Report Chart")
                chartsheet.set_chart(chart)

        return excel_file
    except Exception as e:
        raise RuntimeError(f"Error processing CSV: {str(e)}")
