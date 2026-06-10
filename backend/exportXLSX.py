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
C_PRESS_P5    = '#00BCD4'   # Bright Cyan-Teal
C_EFF_FWD     = '#C0C0C0'   # Silver Gray (Sensor 1)
C_EFF_REV     = '#EB1C23'   # Red (Sensor 3)

C_BORDER_DARK = '#1A2733'   # Header borders
C_ROW_EVEN    = '#EBF0F5'   # Alternating row color
C_GRIDLINE    = '#3D5166'   # Grid lines in the dark chart
C_PLOT_BG     = '#0D1421'   # The "Inner" area of the chart
C_THRESHOLD   = '#39B54A'   # Green — Min Efficiency threshold line
C_EFF_AVG     = '#00E5FF'   # Bright Cyan — Average Efficiency line


def process_csv_to_excel_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as csv_file:
            file_contents = csv_file.read()

        header_keywords = ["Program Name", "Description", "Employee ID", "Comp Set",
                           "Input Factor", "Input Factor Type", "Serial Number", "Customer ID",
                           "Min Efficiency %"]
        float_fields = ["Input Factor", "Serial Number", "Employee ID", "Comp Set", "Customer ID",
                        "Min Efficiency %"]
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

        # Extract optional Min Efficiency % (e.g. 93.0 means 93%)
        min_eff_pct = None
        for r in metadata:
            if r and str(r[0]).strip() == "Min Efficiency %":
                try:
                    min_eff_pct = float(r[1])
                except (ValueError, IndexError, TypeError):
                    pass
                break

        # 1. Theoretical Flow
        def calculate_theo_flow(row):
            rn = row.name + offset + 2
            if is_cu_in:
                return f"=$B${input_factor_row}*{S1_letter}{rn}/231"
            return f"=$B${input_factor_row}*{S1_letter}{rn}*0.0002642"

        df["Theo Flow"] = df.apply(calculate_theo_flow, axis=1)
        FTheo_L = column_letter(df.columns.get_loc("Theo Flow"))

        # 2. Raw Efficiencies (Theo / Sensor + Filter Sensor > 1)
        def raw_eff_f1(row):
            rn = row.name + offset + 2
            expr = f"{F1_letter}{rn}/{FTheo_L}{rn}"
            return f"=IFERROR(IF(${F1_letter}{rn}>1, {expr}, NA()), NA())"

        def raw_eff_f3(row):
            rn = row.name + offset + 2
            expr = f"{F3_letter}{rn}/{FTheo_L}{rn}"
            return f"=IFERROR(IF(${F3_letter}{rn}>1, {expr}, NA()), NA())"

        df["EffRaw_F1"] = df.apply(raw_eff_f1, axis=1)
        df["EffRaw_F3"] = df.apply(raw_eff_f3, axis=1)
        W1_L = column_letter(df.columns.get_loc("EffRaw_F1"))
        W3_L = column_letter(df.columns.get_loc("EffRaw_F3"))

        # 3. Efficiency A & B (Corrected Directional Logic)
        if U_letter and T_trend_letter:
            # Efficiency A: Fwd (Sensor 1) when Reversed is 0
            def eff_a_formula(row):
                rn = row.name + offset + 2
                return f'=IF(AND(${T_trend_letter}{rn}=1,${U_letter}{rn}=0,${W1_L}{rn}>=0.1),${W1_L}{rn},NA())'

            # Efficiency B: Rev (F3) when Reversed is 1
            def eff_b_formula(row):
                rn = row.name + offset + 2
                return f'=IF(AND(${T_trend_letter}{rn}=1,${U_letter}{rn}=1,${W3_L}{rn}>=0.1),${W3_L}{rn},NA())'

            df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
            df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

            # 4. Average Efficiency — omit values below 80% to filter outliers
            def eff_avg_formula(row):
                rn = row.name + offset + 2
                return (f'=IFERROR(IF(AVERAGE(${W1_L}{rn},${W3_L}{rn})>=0.8,'
                        f'AVERAGE(${W1_L}{rn},${W3_L}{rn}),NA()),NA())')

            df["Average Efficiency"] = df.apply(eff_avg_formula, axis=1)

            # 4b. Smoothed Average — computed in Python as STATIC values so it
            # can never evaluate to #N/A (Excel AGGREGATE over the formula-driven
            # Average Efficiency column did not behave reliably). Mirrors the
            # Average Efficiency math, then a centered 7-point moving average that
            # skips the gaps. Falls back to the raw formula column on any error so
            # the export never fails because of smoothing.
            try:
                input_factor_val = 11.0
                for r in metadata:
                    if r and str(r[0]).strip() == "Input Factor":
                        try:
                            input_factor_val = float(r[1])
                        except (ValueError, IndexError, TypeError):
                            pass
                        break

                s1_num = pd.to_numeric(df["S1"], errors="coerce")
                f1_num = pd.to_numeric(df["F1"], errors="coerce")
                f3_num = pd.to_numeric(df["F3"], errors="coerce")
                if is_cu_in:
                    theo_num = input_factor_val * s1_num / 231.0
                else:
                    theo_num = input_factor_val * s1_num * 0.0002642
                e1 = (f1_num / theo_num).where((f1_num > 1) & (theo_num > 0))
                e3 = (f3_num / theo_num).where((f3_num > 1) & (theo_num > 0))
                # build the pair via .values so Series names/index can't interfere
                pair = pd.DataFrame({"e1": e1.to_numpy(), "e3": e3.to_numpy()})
                avg_eff = pair.mean(axis=1)                          # skips NaN
                avg_eff = avg_eff.where(avg_eff >= 0.8)              # drop <80% outliers
                # Wide centered window blends many fwd+rev cycles → a stable,
                # slowly-varying trend instead of tracking each individual cycle.
                smooth = avg_eff.rolling(window=25, center=True, min_periods=1).mean()
                df["Avg Eff (Smooth)"] = smooth.to_numpy()
            except Exception:
                df["Avg Eff (Smooth)"] = df["Average Efficiency"]

        # 5. Min Efficiency Threshold (constant column when provided)
        min_thresh_letter = None
        if min_eff_pct is not None and min_eff_pct > 0:
            df["Min Eff Threshold"] = min_eff_pct / 100.0
            min_thresh_letter = column_letter(df.columns.get_loc("Min Eff Threshold"))

        # --- Excel Export ---
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")

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

            # Deep Auto-fit — str() everything so a stray float/NaN can't break len()
            df_str = df.astype(str)
            for col_idx, col_name in enumerate(df.columns):
                series = df_str.iloc[:, col_idx]
                max_data_len = series.map(lambda v: len(str(v))).max() if len(df) > 0 else 0
                col_width = max(len(str(col_name)), int(max_data_len or 0)) + 2
                worksheet.set_column(col_idx, col_idx, min(col_width, 40))

            # Apply percent formatting
            for col in ["EffRaw_F1", "EffRaw_F3", "Efficiency A", "Efficiency B",
                        "Average Efficiency", "Avg Eff (Smooth)", "Min Eff Threshold"]:
                if col in df.columns:
                    idx = df.columns.get_loc(col)
                    worksheet.set_column(idx, idx, 14, percent_fmt)

            # Alternating row colors
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

                # 1. BASE Chart (Directional Efficiency Columns)
                chart = workbook.add_chart({"type": "column"})
                
                # Fwd Efficiency (Sensor 1) - Silver
                col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                chart.add_series({
                    "name": "Fwd Efficiency (F1)", "categories": time_cats(),
                    "values": f"=Data!${col_ea}${first_row}:${col_ea}${chart_last}",
                    "fill": {"color": C_EFF_FWD, "transparency": 35}, "border": {"none": True},
                })
                # Rev Efficiency (Sensor 3) - Red
                col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                chart.add_series({
                    "name": "Rev Efficiency (F3)", "categories": time_cats(),
                    "values": f"=Data!${col_eb}${first_row}:${col_eb}${chart_last}",
                    "fill": {"color": C_EFF_REV, "transparency": 35}, "border": {"none": True},
                })

                # 2. COMBINE AVERAGE LINE (Forces Excel to draw a line on the primary axis)
                avg_line_chart = workbook.add_chart({"type": "line"})
                col_avg = column_letter(df.columns.get_loc("Average Efficiency"))
                avg_line_chart.add_series({
                    "name": "Average Efficiency", "categories": time_cats(),
                    "values": f"=Data!${col_avg}${first_row}:${col_avg}${chart_last}",
                    "line": {"color": C_WHITE, "width": 2.25},
                })
                chart.combine(avg_line_chart)

                # 3. COMBINE PRESSURE AREAS (Right Axis)
                pressure_chart = workbook.add_chart({"type": "area"})
                pressure_chart.add_series({
                    "name": "P5 Pressure", "categories": time_cats(),
                    "values": f"=Data!${P5_letter}${first_row}:${P5_letter}${chart_last}",
                    "fill": {"color": C_PRESS_P5, "transparency": 65},
                    "border": {"color": C_PRESS_P5, "width": 1}, "y2_axis": True,
                })
                pressure_chart.add_series({
                    "name": "P1 Pressure", "categories": time_cats(),
                    "values": f"=Data!${P1_letter}${first_row}:${P1_letter}${chart_last}",
                    "fill": {"color": C_PRESS_P1, "transparency": 65},
                    "border": {"color": C_PRESS_P1, "width": 1}, "y2_axis": True,
                })
                
                # LC Setpoint Line
                if H_lc_letter:
                    pressure_chart.add_series({
                        "name": "LC Setpoint", "categories": time_cats(),
                        "values": f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${chart_last}",
                        "fill": {"none": True},
                        "line": {"color": C_AMBER, "width": 2, "dash_type": "dash"},
                        "y2_axis": True,
                    })
                chart.combine(pressure_chart)

                # 4. THEME & AXIS STYLING
                chart.set_chartarea({"fill": {"color": C_PLOT_BG}, "border": {"none": True}})
                chart.set_plotarea( {"fill": {"color": C_PLOT_BG}, "border": {"none": True}})
                chart.set_title({"name": "Open Loop Pump Test Profile", "name_font": {"color": C_RED, "size": 16, "bold": True}})

                # X Axis
                chart.set_x_axis({
                    "name": "Time Index", "name_font": {"color": C_WHITE}, 
                    "num_font": {"color": C_WHITE}, "line": {"color": C_WHITE}
                })

                # Y Axis (Left - Efficiency)
                chart.set_y_axis({
                    "name": "Efficiency %", "name_font": {"color": C_WHITE}, 
                    "num_font": {"color": C_WHITE}, "min": 0, "max": 1.1, 
                    "num_format": "0%", "major_gridlines": {"visible": True, "line": {"color": C_GRIDLINE}},
                    "line": {"color": C_WHITE},
                })

                # Y2 Axis (Right - Pressure)
                y2_cfg = {
                    "name": "Pressure (PSI)", "name_font": {"color": C_WHITE},
                    "num_font": {"color": C_WHITE}, "line": {"color": C_WHITE},
                    "min": 0, "max": 3500, "visible": True
                }
                chart.set_y2_axis(y2_cfg)
                pressure_chart.set_y2_axis(y2_cfg)

                chart.set_legend({"position": "bottom", "font": {"color": C_WHITE}})
                chartsheet = workbook.add_chartsheet("Report Chart")
                chartsheet.set_chart(chart)

                # ── Customer Report — two side-by-side charts on one worksheet ──
                # Splitting into two axis-pure charts avoids all the mixed-axis /
                # combine corruption issues:
                #   Pressure chart  → P1, P5, LC Setpoint  (all PSI, one axis)
                #   Efficiency chart→ Fwd, Rev cols + Avg, Min lines (all %, one axis)
                CHART_W, CHART_H = 820, 560

                def _style_chart(c, title):
                    c.set_chartarea({"fill": {"color": C_PLOT_BG}, "border": {"none": True}})
                    c.set_plotarea({"fill": {"color": C_PLOT_BG}, "border": {"none": True}})
                    c.set_title({"name": title, "name_font": {"color": C_RED, "size": 14, "bold": True}})
                    c.set_x_axis({
                        "name": "Time", "name_font": {"color": C_WHITE},
                        "num_font": {"color": C_WHITE, "size": 8}, "line": {"color": C_WHITE},
                    })
                    c.set_legend({"position": "bottom", "font": {"color": C_WHITE}})
                    c.set_size({"width": CHART_W, "height": CHART_H})

                # 1) Pressure chart — all series share the single PSI axis
                press_chart = workbook.add_chart({"type": "line"})
                if P1_letter:
                    press_chart.add_series({
                        "name": "P1 Pressure", "categories": time_cats(),
                        "values": f"=Data!${P1_letter}${first_row}:${P1_letter}${chart_last}",
                        "line": {"color": C_PRESS_P1, "width": 1.75},
                    })
                if P5_letter:
                    press_chart.add_series({
                        "name": "P5 Pressure", "categories": time_cats(),
                        "values": f"=Data!${P5_letter}${first_row}:${P5_letter}${chart_last}",
                        "line": {"color": C_PRESS_P5, "width": 1.75},
                    })
                if H_lc_letter:
                    press_chart.add_series({
                        "name": "LC Setpoint", "categories": time_cats(),
                        "values": f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${chart_last}",
                        "line": {"color": C_AMBER, "width": 1.75, "dash_type": "dash"},
                    })
                press_chart.set_y_axis({
                    "name": "Pressure (PSI)", "name_font": {"color": C_WHITE},
                    "num_font": {"color": C_WHITE}, "min": 0, "max": 3500,
                    "major_gridlines": {"visible": True, "line": {"color": C_GRIDLINE}},
                    "line": {"color": C_WHITE},
                })
                _style_chart(press_chart, "Pressure")

                # 2) Efficiency chart — Fwd/Rev columns + Avg/Min lines, single % axis.
                # column base + line combine, both primary Y → axis-pure, safe.
                eff_chart = workbook.add_chart({"type": "column"})
                col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                eff_chart.add_series({
                    "name": "Fwd Efficiency (F1)", "categories": time_cats(),
                    "values": f"=Data!${col_ea}${first_row}:${col_ea}${chart_last}",
                    "fill": {"color": C_EFF_FWD, "transparency": 35}, "border": {"none": True},
                })
                col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                eff_chart.add_series({
                    "name": "Rev Efficiency (F3)", "categories": time_cats(),
                    "values": f"=Data!${col_eb}${first_row}:${col_eb}${chart_last}",
                    "fill": {"color": C_EFF_REV, "transparency": 35}, "border": {"none": True},
                })
                eff_line_chart = workbook.add_chart({"type": "line"})
                col_avg = column_letter(df.columns.get_loc("Avg Eff (Smooth)"))
                eff_line_chart.add_series({
                    "name": "Average Efficiency", "categories": time_cats(),
                    "values": f"=Data!${col_avg}${first_row}:${col_avg}${chart_last}",
                    "line": {"color": C_EFF_AVG, "width": 3},
                    "smooth": True,
                })
                if min_thresh_letter:
                    eff_line_chart.add_series({
                        "name": f"Min Efficiency ({min_eff_pct:.0f}%)", "categories": time_cats(),
                        "values": f"=Data!${min_thresh_letter}${first_row}:${min_thresh_letter}${chart_last}",
                        "line": {"color": C_THRESHOLD, "width": 2.5, "dash_type": "dash"},
                    })
                eff_chart.combine(eff_line_chart)
                # Connect the Average line across any blank cells so it reads as one
                # continuous trend instead of disconnected segments.
                eff_chart.show_blanks_as("span")
                eff_line_chart.show_blanks_as("span")
                eff_chart.set_y_axis({
                    "name": "Efficiency %", "name_font": {"color": C_WHITE},
                    "num_font": {"color": C_WHITE}, "min": 0, "max": 1.1,
                    "num_format": "0%", "major_gridlines": {"visible": True, "line": {"color": C_GRIDLINE}},
                    "line": {"color": C_WHITE},
                })
                _style_chart(eff_chart, "Efficiency")

                # Place both on a worksheet, side by side.
                cust_ws = workbook.add_worksheet("Customer Report")
                cust_ws.hide_gridlines(2)
                cust_ws.insert_chart(1, 1, press_chart)    # ~B2
                cust_ws.insert_chart(1, 14, eff_chart)     # right of the first chart

        return excel_file
    except Exception as e:
        raise RuntimeError(f"Error processing CSV: {str(e)}")
