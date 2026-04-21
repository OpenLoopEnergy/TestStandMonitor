import pandas as pd
import io
import csv
import os
from backend.time_utils import get_export_now

# Primary logo location. Falls back to the frontend public folder if not found.
_ASSETS_LOGO = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
_FALLBACK_LOGO = os.path.join(os.path.dirname(__file__), "..", "frontend", "teststandfrontend", "public", "logo.png")
LOGO_PATH = _ASSETS_LOGO if os.path.isfile(_ASSETS_LOGO) else _FALLBACK_LOGO

# Brand palette
C_RED      = '#EB1C23'  # Primary
C_BLACK    = '#000000'  # Secondary
C_WHITE    = '#FFFFFF'  # Secondary
C_CHARCOAL = '#2E3E4D'  # Secondary
C_AMBER    = '#ECA400'  # Accent — use sparingly


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
            raise ValueError("Failed to find the data header row in the CSV file (needs at least Time and S1).")

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

        # Column mapping — optional columns guarded with None fallback
        S1_letter      = column_letter(df.columns.get_loc("S1"))
        F1_letter      = column_letter(df.columns.get_loc("F1"))
        B_letter       = column_letter(df.columns.get_loc("Time"))
        U_letter       = column_letter(df.columns.get_loc("TP Reversed")) if "TP Reversed" in df.columns else None
        T_trend_letter = column_letter(df.columns.get_loc("Trending"))    if "Trending"    in df.columns else None
        H_lc_letter    = column_letter(df.columns.get_loc("LCSetpoint"))  if "LCSetpoint"  in df.columns else None
        P1_letter      = column_letter(df.columns.get_loc("P1"))          if "P1"          in df.columns else None
        P5_letter      = column_letter(df.columns.get_loc("P5"))          if "P5"          in df.columns else None

        input_factor_row = metadata_row_indices.get("Input Factor", 5)
        offset = len(metadata) + 1  # blank row between metadata and data headers

        # --- Formula columns ---
        def efficiency_formula(row):
            rn = row.name + offset + 2
            theo = f"($B${input_factor_row}*{S1_letter}{rn}/231)"
            return f"=IFERROR(IF({F1_letter}{rn}/{theo}<0.1,NA(),{F1_letter}{rn}/{theo}),NA())"

        df["EfficiencyRaw"] = df.apply(efficiency_formula, axis=1)
        W_raw_eff = column_letter(df.columns.get_loc("EfficiencyRaw"))

        if U_letter and T_trend_letter:
            def eff_a_formula(row):  # Forward (TP Reversed = 1)
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=1,${U_letter}{prev_rn}=1)),${W_raw_eff}{rn},NA())'

            def eff_b_formula(row):  # Reverse (TP Reversed = 0)
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=0,${U_letter}{prev_rn}=0)),${W_raw_eff}{rn},NA())'

            df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
            df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

        # --- Excel output ---
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")
        has_logo = os.path.isfile(LOGO_PATH)

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            pd.DataFrame(metadata).to_excel(writer, index=False, sheet_name="Data", header=False)
            df.to_excel(writer, index=False, sheet_name="Data", startrow=offset)
            workbook  = writer.book
            worksheet = writer.sheets["Data"]

            # --- Formats ---
            percent_fmt = workbook.add_format({"num_format": "0.0%"})

            # Styled column-header row (charcoal blue background, white bold text)
            header_fmt = workbook.add_format({
                "bold": True,
                "font_color": C_WHITE,
                "bg_color": C_CHARCOAL,
                "border": 1,
                "border_color": C_BLACK,
            })
            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(offset, col_idx, col_name, header_fmt)

            # Metadata label styling (red, bold)
            meta_key_fmt = workbook.add_format({"bold": True, "font_color": C_RED})
            for row_idx, row_data in enumerate(metadata):
                if row_data:
                    worksheet.write(row_idx, 0, row_data[0], meta_key_fmt)

            # Efficiency columns as percent
            if "Efficiency A" in df.columns and "Efficiency B" in df.columns:
                worksheet.set_column(df.columns.get_loc("Efficiency A"),
                                     df.columns.get_loc("Efficiency B"), 13, percent_fmt)

            # Logo on Data sheet — upper-right of the metadata block
            if has_logo:
                worksheet.insert_image(0, 5, LOGO_PATH, {
                    "x_scale": 0.07,
                    "y_scale": 0.07,
                    "object_position": 3,
                })

            # --- Chart ---
            if len(df) > 0:
                first_row, last_row = offset + 2, len(df) + offset + 1

                def time_cats():
                    return f"=Data!${B_letter}${first_row}:${B_letter}${last_row}"

                # Primary area chart — P1 and P5 pressure bands
                chart = workbook.add_chart({"type": "area"})

                if P1_letter:
                    chart.add_series({
                        "name": "P1 Pressure",
                        "categories": time_cats(),
                        "values": f"=Data!${P1_letter}${first_row}:${P1_letter}${last_row}",
                        "fill": {"color": C_CHARCOAL, "transparency": 20},
                        "border": {"none": True},
                    })
                if P5_letter:
                    chart.add_series({
                        "name": "P5 Pressure",
                        "categories": time_cats(),
                        "values": f"=Data!${P5_letter}${first_row}:${P5_letter}${last_row}",
                        "fill": {"color": C_CHARCOAL, "transparency": 45},
                        "border": {"none": True},
                    })

                # LC Setpoint — line only (amber dashed), no area fill
                if H_lc_letter:
                    chart.add_series({
                        "name": "LC Setpoint",
                        "categories": time_cats(),
                        "values": f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${last_row}",
                        "fill": {"none": True},          # no area blob
                        "border": {"color": C_AMBER, "width": 1.5, "dash_type": "dash"},
                    })

                # Efficiency lines on secondary axis
                line_chart = workbook.add_chart({"type": "line"})
                if "Efficiency A" in df.columns:
                    col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                    line_chart.add_series({
                        "name": "Forward Efficiency",
                        "categories": time_cats(),
                        "values": f"=Data!${col_ea}${first_row}:${col_ea}${last_row}",
                        "line": {"color": C_WHITE, "width": 2.5},
                        "y2_axis": True,
                    })
                if "Efficiency B" in df.columns:
                    col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                    line_chart.add_series({
                        "name": "Reverse Efficiency",
                        "categories": time_cats(),
                        "values": f"=Data!${col_eb}${first_row}:${col_eb}${last_row}",
                        "line": {"color": C_RED, "width": 2.5},
                        "y2_axis": True,
                    })
                chart.combine(line_chart)

                # Chart area: charcoal blue background, no border (removes white outline)
                chart.set_chartarea({
                    "fill": {"color": C_CHARCOAL},
                    "border": {"none": True},
                })
                # Plot area: darker navy so data stands out
                chart.set_plotarea({
                    "fill": {"color": "#1A2733"},
                    "border": {"none": True},
                })

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

                # Embed chart in a regular worksheet so the logo can sit alongside it
                chart_ws = workbook.add_worksheet("Report Chart")
                chart_ws.hide_gridlines(2)
                chart_ws.insert_chart("A1", chart, {"x_scale": 3.2, "y_scale": 2.8})

                if has_logo:
                    chart_ws.insert_image(0, 0, LOGO_PATH, {
                        "x_scale": 0.06,
                        "y_scale": 0.06,
                        "x_offset": 1310,
                        "y_offset": 10,
                        "object_position": 3,
                    })

            worksheet.autofilter(offset, 0, last_row, len(df.columns) - 1)

        return excel_file

    except Exception as e:
        raise RuntimeError(f"Error processing CSV: {str(e)}")
