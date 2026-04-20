import pandas as pd
import io
import csv
import os
from backend.time_utils import get_export_now

def process_csv_to_excel_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as csv_file:
            file_contents = csv_file.read()

        header_keywords = [
            "Program Name", "Description", "Employee ID", "Comp Set",
            "Input Factor", "Input Factor Type", "Serial Number", "Customer ID"
        ]
        float_fields = ["Input Factor", "Serial Number", "Employee ID", "Comp Set", "Customer ID"]

        metadata = []
        data_lines = []
        header_row_found = False
        metadata_row_indices = {}

        reader = csv.reader(io.StringIO(file_contents))
        for _, row in enumerate(reader):
            if not row: continue
            if not header_row_found and len(row) >= 2 and any(keyword in row[0] for keyword in header_keywords):
                metadata.append(row)
                field_name = row[0].strip()
                if field_name in float_fields:
                    try:
                        numeric_value = float("".join(c for c in row[1].strip() if c.isdigit() or c == "."))
                        metadata[-1][1] = numeric_value
                    except: metadata[-1][1] = 0.0
                metadata_row_indices[field_name] = len(metadata)
            elif (("Date" in row and "Time" in row and "S1" in row) or ("Time" in row and "S1" in row)):
                header_row_found = True
                data_lines.append(row)
            elif header_row_found:
                data_lines.append(row)

        if not header_row_found:
            raise ValueError("Failed to find data header row.")

        df = pd.read_csv(io.StringIO("\n".join([",".join(map(str, row)) for row in data_lines])))

        # Numeric conversion
        numeric_cols = ["TP", "S1", "F1", "Cycle Timer", "LCSetpoint", "P1", "P5", "TP Reversed", "Trending"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        def column_letter(idx: int) -> str:
            letter = ""
            while idx >= 0:
                letter = chr(ord("A") + idx % 26) + letter
                idx = idx // 26 - 1
            return letter

        # Identify Column Letters for Formulas
        S1_letter = column_letter(df.columns.get_loc("S1"))
        F1_letter = column_letter(df.columns.get_loc("F1"))
        U_letter = column_letter(df.columns.get_loc("TP Reversed"))
        T_trend_letter = column_letter(df.columns.get_loc("Trending"))
        H_lc_letter = column_letter(df.columns.get_loc("LCSetpoint"))
        P1_letter = column_letter(df.columns.get_loc("P1"))
        P5_letter = column_letter(df.columns.get_loc("P5"))

        input_factor_row = metadata_row_indices.get("Input Factor", 5)
        offset = len(metadata) + 1

        # 1. Theo Flow and Raw Efficiency calculation
        def calculate_theo_flow(row):
            rn = row.name + offset + 2
            return f"=$B${input_factor_row}*{S1_letter}{rn}/231"
        
        df["Theo Flow"] = df.apply(calculate_theo_flow, axis=1)
        FTheo_letter = column_letter(df.columns.get_loc("Theo Flow"))

        def efficiency_formula(row):
            rn = row.name + offset + 2
            eff_expr = f"{F1_letter}{rn}/{FTheo_letter}{rn}"
            return f"=IFERROR(IF({eff_expr}<0.1,NA(),{eff_expr}),NA())"

        df["EfficiencyRaw"] = df.apply(efficiency_formula, axis=1)
        W_raw_eff = column_letter(df.columns.get_loc("EfficiencyRaw"))

        # 2. Efficiency A/B (Forward/Reverse) filtered by Trending
        def eff_a_formula(row):
            n = row.name + offset + 2
            prev_n = n - 1 if row.name > 0 else n
            # Logic: If Trending=1 AND (Direction=1 OR PrevDirection=1)
            return f'=IF(AND(${T_trend_letter}{n}=1,OR(${U_letter}{n}=1,${U_letter}{prev_n}=1)),${W_raw_eff}{n},NA())'

        def eff_b_formula(row):
            n = row.name + offset + 2
            prev_n = n - 1 if row.name > 0 else n
            # Logic: If Trending=1 AND (Direction=0 OR PrevDirection=0)
            return f'=IF(AND(${T_trend_letter}{n}=1,OR(${U_letter}{n}=0,${U_letter}{prev_n}=0)),${W_raw_eff}{n},NA())'

        df["Efficiency A"] = df.apply(eff_a_formula, axis=1)
        df["Efficiency B"] = df.apply(eff_b_formula, axis=1)

        # Output Excel
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_excel(writer, index=False, sheet_name="Data", header=False)
            df.to_excel(writer, index=False, sheet_name="Data", startrow=offset)

            workbook = writer.book
            worksheet = writer.sheets["Data"]
            
            # Formats
            float_fmt = workbook.add_format({"num_format": "0.00"})
            percent_fmt = workbook.add_format({"num_format": "0.00%"})

            # Apply specific column formatting
            eff_a_idx = df.columns.get_loc("Efficiency A")
            worksheet.set_column(eff_a_idx, eff_a_idx + 1, 14, percent_fmt)

            # Chart setup
            if len(df) > 0:
                first_row = offset + 2
                last_row = len(df) + offset + 1
                
                # Main Chart: Area for raw P1 and P5
                chart = workbook.add_chart({'type': 'area'})
                
                # Pressure P1 (Raw)
                chart.add_series({
                    'name': 'P1 Pressure',
                    'values': f"=Data!${P1_letter}${first_row}:${P1_letter}${last_row}",
                    'fill': {'color': '#4472C4', 'transparency': 60},
                })
                # Pressure P5 (Raw)
                chart.add_series({
                    'name': 'P5 Pressure',
                    'values': f"=Data!${P5_letter}${first_row}:${P5_letter}${last_row}",
                    'fill': {'color': '#70AD47', 'transparency': 60},
                })
                # LC Setpoint (Raw)
                chart.add_series({
                    'name': 'LC Setpoint',
                    'values': f"=Data!${H_lc_letter}${first_row}:${H_lc_letter}${last_row}",
                    'line': {'color': '#FFC000', 'width': 2},
                })

                # Line Chart: For color-changing Efficiency A/B
                line_chart = workbook.add_chart({'type': 'line'})
                
                col_ea = column_letter(df.columns.get_loc("Efficiency A"))
                line_chart.add_series({
                    'name': 'Eff (Forward)',
                    'values': f"=Data!${col_ea}${first_row}:${col_ea}${last_row}",
                    'line': {'color': '#00B050', 'width': 1.5},
                    'y2_axis': True,
                })
                
                col_eb = column_letter(df.columns.get_loc("Efficiency B"))
                line_chart.add_series({
                    'name': 'Eff (Reverse)',
                    'values': f"=Data!${col_eb}${first_row}:${col_eb}${last_row}",
                    'line': {'color': '#FF0000', 'width': 1.5},
                    'y2_axis': True,
                })

                chart.combine(line_chart)

                # Visual Calibration
                chart.set_title({'name': 'Pressure and Efficiency Profile'})
                chart.set_x_axis({'name': 'Time (Filter Trending for report)'})
                chart.set_y_axis({
                    'name': 'PSI',
                    'min': 0, 'max': 3500, 'major_unit': 500
                })
                chart.set_y2_axis({
                    'name': 'Efficiency %',
                    'min': 0, 'max': 1.1, 'num_format': '0%', 'major_unit': 0.2
                })
                chart.set_legend({'position': 'bottom'})

                chartsheet = workbook.add_chartsheet("Report Chart")
                chartsheet.set_chart(chart)

                # Auto-Filter setup to allow collapsing gaps
                worksheet.autofilter(offset, 0, last_row, len(df.columns) - 1)

        return excel_file
    except Exception as e:
        raise RuntimeError(f"Error processing CSV to Excel: {str(e)}")