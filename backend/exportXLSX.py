import pandas as pd
import io
import csv
import os
from backend.time_utils import get_export_now

# Primary logo — drop your CE Energy PNG at backend/assets/logo.png to override.
_ASSETS_LOGO   = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
_FALLBACK_LOGO = os.path.join(os.path.dirname(__file__), "..", "frontend", "teststandfrontend", "public", "logo.png")
LOGO_PATH = _ASSETS_LOGO if os.path.isfile(_ASSETS_LOGO) else _FALLBACK_LOGO

# Brand palette
C_RED      = '#EB1C23'
C_BLACK    = '#000000'
C_WHITE    = '#FFFFFF'
C_CHARCOAL = '#2E3E4D'
C_AMBER    = '#ECA400'   # accent — sparingly

# Pressure band colours — clearly distinct from each other and from the dark plot background
C_P1 = '#4472C4'   # office blue  — bright, clearly different from charcoal
C_P5 = '#2E3E4D'   # brand charcoal — muted, dark grey-blue


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
            if not row:
                continue
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
            raise ValueError("Failed to find the data header row (needs at least Time and S1).")

        df = pd.read_csv(io.StringIO("\n".join([",".join(map(str, row)) for row in data_lines])))

        for col in ["TP", "S1", "F1", "LCSetpoint", "P1", "P5", "TP Reversed", "Trending"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        def column_letter(idx: int) -> str:
            letter = ""
            while idx >= 0:
                letter = chr(ord("A") + idx % 26) + letter
                idx = idx // 26 - 1
            return letter

        # Column mapping — optional columns get None if absent
        S1_letter      = column_letter(df.columns.get_loc("S1"))
        F1_letter      = column_letter(df.columns.get_loc("F1"))
        B_letter       = column_letter(df.columns.get_loc("Time"))
        U_letter       = column_letter(df.columns.get_loc("TP Reversed")) if "TP Reversed" in df.columns else None
        T_trend_letter = column_letter(df.columns.get_loc("Trending"))    if "Trending"    in df.columns else None
        H_lc_letter    = column_letter(df.columns.get_loc("LCSetpoint"))  if "LCSetpoint"  in df.columns else None
        P1_letter      = column_letter(df.columns.get_loc("P1"))          if "P1"          in df.columns else None
        P5_letter      = column_letter(df.columns.get_loc("P5"))          if "P5"          in df.columns else None

        input_factor_row = metadata_row_indices.get("Input Factor", 5)
        offset = len(metadata) + 1   # 0-based row index of the column-header row

        # --- Formula columns ---
        def efficiency_formula(row):
            rn = row.name + offset + 2
            theo = f"($B${input_factor_row}*{S1_letter}{rn}/231)"
            return f"=IFERROR(IF({F1_letter}{rn}/{theo}<0.1,NA(),{F1_letter}{rn}/{theo}),NA())"

        df["EfficiencyRaw"] = df.apply(efficiency_formula, axis=1)
        W_raw_eff = column_letter(df.columns.get_loc("EfficiencyRaw"))

        if U_letter and T_trend_letter:
            def eff_a_formula(row):
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=1,${U_letter}{prev_rn}=1)),${W_raw_eff}{rn},NA())'

            def eff_b_formula(row):
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=0,${U_letter}{prev_rn}=0)),${W_raw_eff}{rn},NA())'

            df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
            df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

        # --- Excel output ---
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")
        has_logo   = os.path.isfile(LOGO_PATH)

        # Formula columns — use header length for width (formula strings are huge)
        FORMULA_COLS = {"EfficiencyRaw", "Efficiency A", "Efficiency B"}

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            pd.DataFrame(metadata).to_excel(writer, index=False, sheet_name="Data", header=False)
            df.to_excel(writer, index=False, sheet_name="Data", startrow=offset)
            workbook  = writer.book
            worksheet = writer.sheets["Data"]

            # ── Formats ─────────────────────────────────────────────────────
            percent_fmt  = workbook.add_format({"num_format": "0.0%"})
            header_fmt   = workbook.add_format({
                "bold": True, "font_color": C_WHITE,
                "bg_color": C_CHARCOAL,
                "border": 1, "border_color": "#1A2733",
            })
            meta_key_fmt = workbook.add_format({"bold": True, "font_color": C_RED})
            even_fmt     = workbook.add_format({"bg_color": "#EBF0F5"})   # light blue-grey
            odd_fmt      = workbook.add_format({"bg_color": C_WHITE})

            # ── Column-header row ────────────────────────────────────────────
            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(offset, col_idx, col_name, header_fmt)

            # ── Metadata key labels ─────────────────────────────────────────
            for row_idx, row_data in enumerate(metadata):
                if row_data:
                    worksheet.write(row_idx, 0, row_data[0], meta_key_fmt)

            # ── Auto-fit column widths ──────────────────────────────────────
            df_str = df.astype(str)
            for col_idx, col_name in enumerate(df.columns):
                if col_name in FORMULA_COLS:
                    # Formula cells display short numbers — size by header name only
                    col_width = len(col_name) + 2
                else:
                    max_data_len = df_str[col_name].map(len).max() if len(df) > 0 else 0
                    col_width = max(len(col_name), max_data_len) + 2
                    # Also check metadata values in columns 0 and 1
                    if col_idx == 0:
                        col_width = max(col_width, max((len(str(r[0])) for r in metadata if r), default=0) + 2)
                    elif col_idx == 1:
                        col_width = max(col_width, max((len(str(r[1])) for r in metadata if len(r) > 1), default=0) + 2)
                # Cap very wide columns (long step names etc.)
                col_width = min(col_width, 40)
                worksheet.set_column(col_idx, col_idx, col_width)

            # Re-apply percent format to efficiency columns after set_column
            if "Efficiency A" in df.columns and "Efficiency B" in df.columns:
                worksheet.set_column(df.columns.get_loc("Efficiency A"),
                                     df.columns.get_loc("Efficiency B"), 14, percent_fmt)

            # ── Alternating row colours ─────────────────────────────────────
            last_row   = len(df) + offset + 1   # 0-based last data row
            num_cols   = len(df.columns) - 1
            data_start = offset + 1              # 0-based first data row
            worksheet.conditional_format(data_start, 0, last_row, num_cols, {
                "type": "formula", "criteria": "=MOD(ROW(),2)=0", "format": even_fmt,
            })
            worksheet.conditional_format(data_start, 0, last_row, num_cols, {
                "type": "formula", "criteria": "=MOD(ROW(),2)=1", "format": odd_fmt,
            })

            worksheet.autofilter(offset, 0, last_row, num_cols)

            # ── Logo on Data sheet — prominent, upper-right of metadata ─────
            if has_logo:
                worksheet.insert_image(0, 9, LOGO_PATH, {
                    "x_scale": 0.45,
                    "y_scale": 0.45,
                    "object_position": 3,
                })

            # ── Chart ────────────────────────────────────────────────────────
            if len(df) > 0:
                first_row  = offset + 2
                chart_last = len(df) + offset + 1

                def time_cats():
                    return f"=Data!${B_letter}${first_row}:${B_letter}${chart_last}"

                # Primary area chart — P5 behind P1 so P1 is always visible on top
                chart = workbook.add_chart({"type": "area"})

                if P5_letter:
                    chart.add_series({
                        "name": "P5 Pressure",
                        "categories": time_cats(),
                        "values": f"=Data!${P5_letter}${first_row}:${P5_letter}${chart_last}",
                        "fill":   {"color": C_P5, "transparency": 15},
                        "border": {"none": True},
                    })
                if P1_letter:
                    chart.add_series({
                        "name": "P1 Pressure",
                        "categories": time_cats(),
                        "values": f"=Data!${P1_letter}${first_row}:${P1_letter}${chart_last}",
                        "fill":   {"color": C_P1, "transparency": 15},
                        "border": {"none": True},
                    })

                # Secondary line chart — efficiency (y2) and LC Setpoint (y1, drawn last = on top)
                # Configuring the y2 axis on line_chart BEFORE combining is required for
                # white axis labels to render correctly in combined charts.
                line_chart = workbook.add_chart({"type": "line"})

                if "Efficiency A" in df.columns:
                    col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                    line_chart.add_series({
                        "name": "Forward Efficiency",
                        "categories": time_cats(),
                        "values": f"=Data!${col_ea}${first_row}:${col_ea}${chart_last}",
                        "line":  {"color": C_WHITE, "width": 1.75},
                        "y2_axis": True,
                    })
                if "Efficiency B" in df.columns:
                    col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                    line_chart.add_series({
                        "name": "Reverse Efficiency",
                        "categories": time_cats(),
                        "values": f"=Data!${col_eb}${first_row}:${col_eb}${chart_last}",
                        "line":  {"color": C_RED, "width": 1.75},
                        "y2_axis": True,
                    })

                # LC Setpoint added LAST to line_chart so it renders on top of everything.
                # y2_axis=False keeps it on the primary (PSI) scale.
                if H_lc_letter:
                    line_chart.add_series({
                        "name": "LC Setpoint",
                        "categories": time_cats(),
                        "values": f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${chart_last}",
                        "line":  {"color": C_AMBER, "width": 1.75, "dash_type": "dash"},
                        "y2_axis": False,
                    })

                # Set y2 axis on line_chart BEFORE combining — this is required for
                # the white font colour to apply correctly to the right-hand axis labels.
                line_chart.set_y_axis({
                    "name": "Efficiency %",
                    "name_font": {"color": C_WHITE},
                    "num_font":  {"color": C_WHITE},
                    "min": 0, "max": 1.1, "major_unit": 0.1,
                    "num_format": "0%",
                    "major_gridlines": {"visible": False},
                })

                chart.combine(line_chart)

                # Chart / plot area theming
                chart.set_chartarea({"fill": {"color": C_CHARCOAL}, "border": {"none": True}})
                chart.set_plotarea( {"fill": {"color": "#0D1421"},   "border": {"none": True}})

                chart.set_title({
                    "name": "Open Loop Pump Test: Pressure & Efficiency",
                    "name_font": {"color": C_RED, "size": 16, "bold": True},
                })
                chart.set_x_axis({
                    "name": "Time",
                    "name_font": {"color": C_WHITE},
                    "num_font":  {"color": C_WHITE},
                    "line":      {"color": C_WHITE},
                    "major_gridlines": {"visible": False},
                })
                chart.set_y_axis({
                    "name": "PSI",
                    "name_font": {"color": C_WHITE},
                    "num_font":  {"color": C_WHITE},
                    "line":      {"color": C_WHITE},
                    "min": 0, "max": 3500,
                    "major_gridlines": {"visible": True, "line": {"color": "#3D5166"}},
                })
                # Also call set_y2_axis on the primary chart for belt-and-suspenders
                chart.set_y2_axis({
                    "name": "Efficiency %",
                    "name_font": {"color": C_WHITE},
                    "num_font":  {"color": C_WHITE},
                    "min": 0, "max": 1.1, "major_unit": 0.1,
                    "num_format": "0%",
                    "major_gridlines": {"visible": False},
                })
                chart.set_legend({
                    "position": "bottom",
                    "font": {"color": C_WHITE},
                })

                # Chart sheet: chart at A1, logo anchored at column 24 (just past the
                # chart's ~1440px width). x_offset MUST stay ≤ 1023 or xlsxwriter
                # writes invalid drawing XML — never compute it from chart scale again.
                CHART_SCALE_X  = 3.0
                CHART_SCALE_Y  = 2.9
                LOGO_SCALE     = 0.45   # 546*0.45=246px wide, 324*0.45=146px tall
                LOGO_COL       = 23     # col index 23 (~1449px from A1) clears the 1440px chart
                LOGO_X_OFFSET  = 20     # small gap, well within the 1023-pixel limit

                chart_ws = workbook.add_worksheet("Report Chart")
                chart_ws.hide_gridlines(2)
                chart_ws.insert_chart("A1", chart, {"x_scale": CHART_SCALE_X, "y_scale": CHART_SCALE_Y})

                if has_logo:
                    chart_ws.insert_image(0, LOGO_COL, LOGO_PATH, {
                        "x_scale": LOGO_SCALE,
                        "y_scale": LOGO_SCALE,
                        "x_offset": LOGO_X_OFFSET,
                        "y_offset": 30,
                        "object_position": 3,
                    })

        return excel_file

    except Exception as e:
        raise RuntimeError(f"Error processing CSV: {str(e)}")
