import pandas as pd
import io
import csv
import os

from backend.time_utils import get_export_now

STEP_MATCH_LIST = '{"B53","B57","B59","B56","B52","B35","B11","B60"}'

def process_csv_to_excel_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as csv_file:
            file_contents = csv_file.read()

        header_keywords = [
            "Program Name",
            "Description",
            "Employee ID",
            "Comp Set",
            "Input Factor",
            "Input Factor Type",
            "Serial Number",
            "Customer ID",
        ]
        float_fields = ["Input Factor", "Serial Number", "Employee ID", "Comp Set", "Customer ID"]

        metadata = []
        data_lines = []
        header_row_found = False
        metadata_row_indices = {}

        reader = csv.reader(io.StringIO(file_contents))
        for _, row in enumerate(reader):
            if not row:
                continue

            # Metadata rows: first cell matches known keys
            if (
                not header_row_found
                and len(row) >= 2
                and any(keyword in row[0] for keyword in header_keywords)
            ):
                metadata.append(row)
                field_name = row[0].strip()

                if field_name in float_fields:
                    try:
                        numeric_value = float("".join(c for c in row[1].strip() if c.isdigit() or c == "."))
                        metadata[-1][1] = numeric_value
                    except (ValueError, AttributeError):
                        metadata[-1][1] = 0.0


                # 1-based row index for Excel reference
                metadata_row_indices[field_name] = len(metadata)

            # Header row detection: allow both old style (Date+Time+S1) and new style (Time+S1)
            elif (("Date" in row and "Time" in row and "S1" in row) or ("Time" in row and "S1" in row)):
                header_row_found = True
                data_lines.append(row)

            elif header_row_found:
                data_lines.append(row)

        if not header_row_found:
            raise ValueError("Failed to find the data header row in the CSV file (needs at least Time and S1).")

        metadata_df = pd.DataFrame(metadata)

        data_text = "\n".join([",".join(map(str, row)) for row in data_lines])
        data_csv = io.StringIO(data_text)
        df = pd.read_csv(data_csv)

        print("DF columns:", list(df.columns))
        print("First row:", df.head(1).to_dict(orient="records"))

        # Required columns check (fail fast with a useful message)
        required_cols = ["Time", "S1", "TP", "F1"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}. Found columns: {list(df.columns)}")

        # Convert core columns to numeric
        df["TP"] = pd.to_numeric(df["TP"], errors="coerce")
        df["S1"] = pd.to_numeric(df["S1"], errors="coerce")
        df["F1"] = pd.to_numeric(df["F1"], errors="coerce")
        df["Cycle Timer"] = pd.to_numeric(df["Cycle Timer"], errors="coerce")

        # F1 scaling: export_csv() already scales F1 from centi-units (* 0.01).
        # Do NOT apply scaling again here. If for some reason you receive raw
        # (unscaled) CSV data, uncomment the block below:
        # f1_median = df["F1"].median(skipna=True)
        # if pd.notna(f1_median) and f1_median > 200:
        #     df["F1"] = df["F1"] * 0.01

        # Use all rows — no filtering
        df_filtered = df.reset_index(drop=True)
        if df_filtered.empty:
            raise ValueError("No data rows to export.")

        # Helpers
        def column_letter(idx: int) -> str:
            letter = ""
            while idx >= 0:
                letter = chr(ord("A") + idx % 26) + letter
                idx = idx // 26 - 1
            return letter

        # Column letters based on df_filtered layout
        S1_letter = column_letter(df_filtered.columns.get_loc("S1"))
        F1_letter = column_letter(df_filtered.columns.get_loc("F1"))

        input_factor_row = metadata_row_indices.get("Input Factor", None)
        if input_factor_row is None:
            raise ValueError("Input Factor row index not found in metadata.")

        # Detect Input Factor type from metadata
        input_factor_type = None
        for r in metadata:
            if r and str(r[0]).strip() == "Input Factor Type":
                input_factor_type = str(r[1]).strip().lower()
                break

        # Default to cu/in if missing
        is_cu_in = True
        if input_factor_type:
            if "cu/cm" in input_factor_type:
                is_cu_in = False
            elif "cu/in" in input_factor_type:
                is_cu_in = True

        # Row offset: metadata then a blank row, then header row, then data
        offset = len(metadata) + 1

        def calculate_theo_flow(row):
            row_num = row.name + offset + 2 # First data row in Excel
            if is_cu_in:
                return f"=$B${input_factor_row}*{S1_letter}{row_num}/231"
            # cu/cm conversion like the macro
            return f"=$B${input_factor_row}*{S1_letter}{row_num}*0.0002642"

        df_filtered["Theo Flow"] = df_filtered.apply(calculate_theo_flow, axis=1)
        FTheo_letter = column_letter(df_filtered.columns.get_loc("Theo Flow"))

        def efficiency_formula(row):
            row_num = row.name + offset + 2
            eff_expr = f"{F1_letter}{row_num}/{FTheo_letter}{row_num}"
            # If efficiency < 80%, return NA() so Excel charts skip the point; return 0 on error
            return f"=IFERROR(IF({eff_expr}<0.8,NA(),{eff_expr}),0)"

        df_filtered["Efficiency"] = df_filtered.apply(efficiency_formula, axis=1)

        # Letters needed for new formula columns
        W_letter = column_letter(df_filtered.columns.get_loc("Efficiency"))
        B_letter = column_letter(df_filtered.columns.get_loc("Time"))

        # Optional columns used by the filtered/analysis columns
        has_step = "Step" in df_filtered.columns
        has_tp_reversed = "TP Reversed" in df_filtered.columns
        has_lc_setpoint = "LCSetpoint" in df_filtered.columns
        has_p1 = "P1" in df_filtered.columns
        has_p5 = "P5" in df_filtered.columns

        if has_step:
            J_letter = column_letter(df_filtered.columns.get_loc("Step"))
            U_letter = column_letter(df_filtered.columns.get_loc("TP Reversed")) if has_tp_reversed else None
            H_letter = column_letter(df_filtered.columns.get_loc("LCSetpoint")) if has_lc_setpoint else None
            P1_letter = column_letter(df_filtered.columns.get_loc("P1")) if has_p1 else None
            P5_letter = column_letter(df_filtered.columns.get_loc("P5")) if has_p5 else None

            def _match(n):
                return f'ISNUMBER(MATCH(LEFT(${J_letter}{n},3),{STEP_MATCH_LIST},0))'

            def eff_a_formula(row):
                n = row.name + offset + 2
                u = f'${U_letter}{n}' if U_letter else '0'
                u_prev = f'${U_letter}{n - 1}' if U_letter else '0'
                return f'=IF(AND(OR({u}=1,{u_prev}=1),{_match(n)}),${W_letter}{n},NA())'

            def eff_b_formula(row):
                n = row.name + offset + 2
                u = f'${U_letter}{n}' if U_letter else '0'
                u_prev = f'${U_letter}{n - 1}' if U_letter else '0'
                return f'=IF(AND(OR({u}=0,{u_prev}=0),{_match(n)}),${W_letter}{n},NA())'

            def lc_formula(row):
                n = row.name + offset + 2
                val = f'${H_letter}{n}' if H_letter else '0'
                return f'=IF({_match(n)},{val},NA())'

            def pressure_a_formula(row):
                n = row.name + offset + 2
                val = f'${P1_letter}{n}' if P1_letter else '0'
                return f'=IF({_match(n)},{val},NA())'

            def pressure_b_formula(row):
                n = row.name + offset + 2
                val = f'${P5_letter}{n}' if P5_letter else '0'
                return f'=IF({_match(n)},{val},NA())'

            def time_filtered_formula(row):
                n = row.name + offset + 2
                return f'=IF({_match(n)},${B_letter}{n},NA())'

            def filter_helper_formula(row):
                n = row.name + offset + 2
                return f'=ISNUMBER(MATCH(LEFT(${J_letter}{n},3),{STEP_MATCH_LIST},0))'

            df_filtered["Efficiency A"] = df_filtered.apply(eff_a_formula, axis=1)
            df_filtered["Efficiency B"] = df_filtered.apply(eff_b_formula, axis=1)
            df_filtered["LC"] = df_filtered.apply(lc_formula, axis=1)
            df_filtered["Pressure A"] = df_filtered.apply(pressure_a_formula, axis=1)
            df_filtered["Pressure B"] = df_filtered.apply(pressure_b_formula, axis=1)
            df_filtered["Time(filtered)"] = df_filtered.apply(time_filtered_formula, axis=1)
            df_filtered["Filter Helper"] = df_filtered.apply(filter_helper_formula, axis=1)

        # Output path
        timestamp = get_export_now().strftime("%m-%d-%Y_%I-%M-%S_%p")
        excel_file = os.path.join(os.path.dirname(file_path), f"TestResults_{timestamp}.xlsx")

        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            # Write metadata (no headers)
            metadata_df.to_excel(writer, index=False, sheet_name="Data", header=False)

            # Write data starting after metadata + 1 blank row
            metadata_rows = len(metadata_df) + 1
            df_filtered.to_excel(writer, index=False, sheet_name="Data", startrow=metadata_rows)

            workbook = writer.book
            worksheet = writer.sheets["Data"]

            # Auto-fit columns (basic)
            all_data = df_filtered.astype(str)
            for col_idx, col in enumerate(df_filtered.columns):
                max_len = len(col)
                for val in all_data[col]:
                    if len(val) > max_len:
                        max_len = len(val)

                # Include metadata width in first column
                if col_idx == 0:
                    for mrow in metadata:
                        for cell in mrow:
                            max_len = max(max_len, len(str(cell)))

                worksheet.set_column(col_idx, col_idx, max_len + 2)

            # Override formatting for specific columns
            float_format = workbook.add_format({"num_format": "0.00"})
            percent_format = workbook.add_format({"num_format": "0.00%"})

            theo_flow_col_index = df_filtered.columns.get_loc("Theo Flow")
            worksheet.set_column(theo_flow_col_index, theo_flow_col_index, 10, float_format)

            efficiency_col_index = df_filtered.columns.get_loc("Efficiency")
            worksheet.set_column(efficiency_col_index, efficiency_col_index, 10, percent_format)

            f1_col_index = df_filtered.columns.get_loc("F1")
            worksheet.set_column(f1_col_index, f1_col_index, 10, float_format)

            if has_step:
                for col_name in ("Efficiency A", "Efficiency B"):
                    if col_name in df_filtered.columns:
                        ci = df_filtered.columns.get_loc(col_name)
                        worksheet.set_column(ci, ci, 14, percent_format)

            # Charts
            if len(df_filtered) > 0:
                header_row_xl = metadata_rows + 1   # 1-indexed Excel row of column headers
                first_data_row = metadata_rows + 2
                last_data_row = len(df_filtered) + metadata_rows + 1

                eff_letter = column_letter(efficiency_col_index)

                # Chart 1 — Efficiency Percentage (original)
                chart1 = workbook.add_chart({"type": "line"})
                chart1.add_series(
                    {
                        "name": "Efficiency (%)",
                        "values": f"=Data!${eff_letter}${first_data_row}:${eff_letter}${last_data_row}",
                        "marker": {"type": "circle"},
                    }
                )
                chart1.set_title({"name": "Efficiency Percentage"})
                chart1.set_x_axis({"name": "Index"})
                chart1.set_y_axis({"name": "Efficiency (%)", "min": 0, "max": 1.1, "major_unit": 0.1})
                chartsheet1 = workbook.add_chartsheet("Chart")
                chartsheet1.set_chart(chart1)

                if has_step and "Efficiency A" in df_filtered.columns:
                    X_letter = column_letter(df_filtered.columns.get_loc("Efficiency A"))
                    Y_letter = column_letter(df_filtered.columns.get_loc("Efficiency B"))
                    Z_letter = column_letter(df_filtered.columns.get_loc("LC"))
                    AA_letter = column_letter(df_filtered.columns.get_loc("Pressure A"))
                    AB_letter = column_letter(df_filtered.columns.get_loc("Pressure B"))
                    AC_letter = column_letter(df_filtered.columns.get_loc("Time(filtered)"))

                    # Chart 2 — LCSetpoint (column) + Efficiency A/B (line)
                    chart2_col = workbook.add_chart({"type": "column", "subtype": "clustered"})
                    if has_lc_setpoint:
                        H_chart_letter = column_letter(df_filtered.columns.get_loc("LCSetpoint"))
                        chart2_col.add_series({
                            "name": f"=Data!${H_chart_letter}${header_row_xl}",
                            "values": f"=Data!${H_chart_letter}${first_data_row}:${H_chart_letter}${last_data_row}",
                        })

                    chart2_line = workbook.add_chart({"type": "line"})
                    chart2_line.add_series({
                        "name": f"=Data!${X_letter}${header_row_xl}",
                        "categories": f"=Data!${B_letter}${header_row_xl}:${B_letter}${last_data_row}",
                        "values": f"=Data!${X_letter}${first_data_row}:${X_letter}${last_data_row}",
                    })
                    chart2_line.add_series({
                        "name": f"=Data!${Y_letter}${header_row_xl}",
                        "categories": f"=Data!${B_letter}${header_row_xl}:${B_letter}${last_data_row}",
                        "values": f"=Data!${Y_letter}${first_data_row}:${Y_letter}${last_data_row}",
                    })

                    chart2_col.combine(chart2_line)
                    chartsheet2 = workbook.add_chartsheet("Chart2")
                    chartsheet2.set_chart(chart2_col)

                    # Chart 3 — Pressure and Efficiency (column + line with secondary axis)
                    chart3_col = workbook.add_chart({"type": "column", "subtype": "clustered"})
                    chart3_col.add_series({
                        "name": f"=Data!${AA_letter}${header_row_xl}",
                        "categories": f"=Data!${AC_letter}${first_data_row}:${AC_letter}${last_data_row}",
                        "values": f"=Data!${AA_letter}${first_data_row}:${AA_letter}${last_data_row}",
                    })
                    chart3_col.add_series({
                        "name": f"=Data!${AB_letter}${header_row_xl}",
                        "categories": f"=Data!${AC_letter}${first_data_row}:${AC_letter}${last_data_row}",
                        "values": f"=Data!${AB_letter}${first_data_row}:${AB_letter}${last_data_row}",
                    })
                    chart3_col.add_series({
                        "name": f"=Data!${Z_letter}${header_row_xl}",
                        "categories": f"=Data!${AC_letter}${first_data_row}:${AC_letter}${last_data_row}",
                        "values": f"=Data!${Z_letter}${first_data_row}:${Z_letter}${last_data_row}",
                    })
                    chart3_col.set_title({"name": "Pressure and Efficiency"})
                    chart3_col.set_x_axis({"name": "Time"})
                    chart3_col.set_y_axis({"name": "PSI"})

                    chart3_line = workbook.add_chart({"type": "line"})
                    chart3_line.add_series({
                        "name": f"=Data!${X_letter}${header_row_xl}",
                        "categories": f"=Data!${AC_letter}${first_data_row}:${AC_letter}${last_data_row}",
                        "values": f"=Data!${X_letter}${first_data_row}:${X_letter}${last_data_row}",
                        "y2_axis": 1,
                    })
                    chart3_line.add_series({
                        "name": f"=Data!${Y_letter}${header_row_xl}",
                        "categories": f"=Data!${AC_letter}${first_data_row}:${AC_letter}${last_data_row}",
                        "values": f"=Data!${Y_letter}${first_data_row}:${Y_letter}${last_data_row}",
                        "y2_axis": 1,
                    })
                    chart3_line.set_y2_axis({"name": "Efficiency"})

                    chart3_col.combine(chart3_line)
                    chartsheet3 = workbook.add_chartsheet("Chart3")
                    chartsheet3.set_chart(chart3_col)

        return excel_file

    except Exception as e:
        raise RuntimeError(f"Error processing CSV to Excel: {str(e)}")
