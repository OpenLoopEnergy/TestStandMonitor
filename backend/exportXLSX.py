import pandas as pd
import io
import csv
import os
from backend.time_utils import get_export_now

# Save your logo PNG to this path — used on both the Data sheet and chart tab
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")


def process_csv_to_excel_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as csv_file:
            file_contents = csv_file.read()

        header_keywords = ["Program Name", "Description", "Employee ID", "Comp Set", "Input Factor", "Input Factor Type", "Serial Number", "Customer ID"]
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

        # Column mapping
        S1_letter = column_letter(df.columns.get_loc("S1"))
        F1_letter = column_letter(df.columns.get_loc("F1"))
        B_letter = column_letter(df.columns.get_loc("Time"))
        U_letter = column_letter(df.columns.get_loc("TP Reversed")) if "TP Reversed" in df.columns else None
        T_trend_letter = column_letter(df.columns.get_loc("Trending")) if "Trending" in df.columns else None
        H_lc_letter = column_letter(df.columns.get_loc("LCSetpoint")) if "LCSetpoint" in df.columns else None
        P1_letter = column_letter(df.columns.get_loc("P1")) if "P1" in df.columns else None
        P5_letter = column_letter(df.columns.get_loc("P5")) if "P5" in df.columns else None
        input_factor_row = metadata_row_indices.get("Input Factor", 5)
        offset = len(metadata) + 1

        # Efficiency formula columns
        def efficiency_formula(row):
            rn = row.name + offset + 2
            theo = f"($B${input_factor_row}*{S1_letter}{rn}/231)"
            return f"=IFERROR(IF({F1_letter}{rn}/{theo}<0.1,NA(),{F1_letter}{rn}/{theo}),NA())"

        df["EfficiencyRaw"] = df.apply(efficiency_formula, axis=1)
        W_raw_eff = column_letter(df.columns.get_loc("EfficiencyRaw"))

        if U_letter and T_trend_letter:
            def eff_a_formula(row):  # Forward
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=1,${U_letter}{prev_rn}=1)),${W_raw_eff}{rn},NA())'

            def eff_b_formula(row):  # Reverse
                rn = row.name + offset + 2
                prev_rn = rn - 1 if row.name > 0 else rn
                return f'=IF(AND(${T_trend_letter}{rn}=1,OR(${U_letter}{rn}=0,${U_letter}{prev_rn}=0)),${W_raw_eff}{rn},NA())'

            df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
            df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

        # Output path
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")

        has_logo = os.path.isfile(LOGO_PATH)

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            pd.DataFrame(metadata).to_excel(writer, index=False, sheet_name="Data", header=False)
            df.to_excel(writer, index=False, sheet_name="Data", startrow=offset)
            workbook, worksheet = writer.book, writer.sheets["Data"]

            # Theme colours
            logo_red = '#EB1C23'
            white = '#FFFFFF'
            black = '#000000'
            dark_grid = '#404040'

            # Column formatting
            percent_fmt = workbook.add_format({"num_format": "0.0%"})
            if "Efficiency A" in df.columns and "Efficiency B" in df.columns:
                worksheet.set_column(df.columns.get_loc("Efficiency A"), df.columns.get_loc("Efficiency B"), 12, percent_fmt)

            # Logo on Data sheet — top-right of the metadata block
            if has_logo:
                worksheet.insert_image(0, 5, LOGO_PATH, {
                    'x_scale': 0.07,
                    'y_scale': 0.07,
                    'object_position': 3,  # Don't move or resize with cells
                })

            # Chart
            if len(df) > 0:
                first_row, last_row = offset + 2, len(df) + offset + 1

                # Helper to build the category reference (Time column)
                def time_cats():
                    return f"=Data!${B_letter}${first_row}:${B_letter}${last_row}"

                # Area chart — pressure background + LC setpoint
                chart = workbook.add_chart({'type': 'area'})
                if P1_letter:
                    chart.add_series({
                        'name': 'P1 PSI',
                        'categories': time_cats(),
                        'values': f"=Data!${P1_letter}${first_row}:${P1_letter}${last_row}",
                        'fill': {'color': '#2F4F4F', 'transparency': 30},
                    })
                if P5_letter:
                    chart.add_series({
                        'name': 'P5 PSI',
                        'categories': time_cats(),
                        'values': f"=Data!${P5_letter}${first_row}:${P5_letter}${last_row}",
                        'fill': {'color': '#1A1A1A', 'transparency': 10},
                    })
                if H_lc_letter:
                    chart.add_series({
                        'name': 'LC Setpoint',
                        'categories': time_cats(),
                        'values': f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${last_row}",
                        'line': {'color': white, 'width': 1.5, 'dash_type': 'dash'},
                    })

                # Line chart overlay — efficiency on secondary axis
                line_chart = workbook.add_chart({'type': 'line'})
                if "Efficiency A" in df.columns:
                    col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                    line_chart.add_series({
                        'name': 'Forward Eff',
                        'categories': time_cats(),
                        'values': f"=Data!${col_ea}${first_row}:${col_ea}${last_row}",
                        'line': {'color': '#00FFFF', 'width': 2.5},
                        'y2_axis': True,
                    })
                if "Efficiency B" in df.columns:
                    col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                    line_chart.add_series({
                        'name': 'Reverse Eff',
                        'categories': time_cats(),
                        'values': f"=Data!${col_eb}${first_row}:${col_eb}${last_row}",
                        'line': {'color': logo_red, 'width': 2.5},
                        'y2_axis': True,
                    })
                chart.combine(line_chart)

                # Dark theme styling
                chart.set_chartarea({'fill': {'color': black}})
                chart.set_plotarea({'fill': {'color': black}})
                chart.set_title({
                    'name': 'Open Loop Pump Test Profile',
                    'name_font': {'color': logo_red, 'size': 18, 'bold': True}
                })
                chart.set_x_axis({
                    'name': 'Time',
                    'name_font': {'color': white},
                    'num_font': {'color': white},
                    'line': {'color': white},
                })
                chart.set_y_axis({
                    'name': 'Pressure (PSI)',
                    'name_font': {'color': white},
                    'num_font': {'color': white},
                    'max': 3500,
                    'major_gridlines': {'visible': True, 'line': {'color': dark_grid}},
                })
                chart.set_y2_axis({
                    'name': 'Efficiency %',
                    'name_font': {'color': white},
                    'num_font': {'color': white},
                    'min': 0,
                    'max': 1.1,
                    'major_unit': 0.1,  # Forces Excel to respect 1.1 max (no auto round-up to 1.2)
                    'num_format': '0%',
                    'major_gridlines': {'visible': False},
                })
                chart.set_legend({'position': 'bottom', 'font': {'color': white}})

                # Use a regular worksheet (not chartsheet) so we can embed the logo
                chart_ws = workbook.add_worksheet("Report Chart")
                chart_ws.hide_gridlines(2)
                chart_ws.insert_chart('A1', chart, {'x_scale': 3.0, 'y_scale': 2.5})

                # Logo on chart tab — upper-right corner of the chart area
                if has_logo:
                    chart_ws.insert_image(0, 0, LOGO_PATH, {
                        'x_scale': 0.06,
                        'y_scale': 0.06,
                        'x_offset': 1260,
                        'y_offset': 12,
                        'object_position': 3,
                    })

            worksheet.autofilter(offset, 0, last_row, len(df.columns) - 1)

        return excel_file

    except Exception as e:
        raise RuntimeError(f"Error: {str(e)}")
